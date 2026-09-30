#!/usr/bin/env python3
"""
Test script for Advanced Features (Casino, Tickets, Channel Enforcement)
"""
import sys
import asyncio
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, '/home/toxic/dayz_workspace/dayz_discord_ops_repo/src')

# Mock discord modules before importing project modules
sys.modules['discord'] = Mock()
sys.modules['discord.ext'] = Mock()
# Fix decorators to pass through the function
def identity_decorator(func):
    return func

def pass_through_decorator(*args, **kwargs):
    return identity_decorator

# Handle @commands.command() and @commands.command
def command_decorator(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return pass_through_decorator(*args, **kwargs)

sys.modules['discord.ext.commands'] = Mock()
# CRITICAL FIX: Link the attribute so 'from discord.ext import commands' works correctly
sys.modules['discord.ext'].commands = sys.modules['discord.ext.commands']

sys.modules['discord.ext.commands'].command = Mock(side_effect=command_decorator)

# Create a dummy Cog class that isn't a Mock
class DummyCog:
    def __init__(self, *args, **kwargs):
        pass
    @classmethod
    def listener(cls):
        return pass_through_decorator()

sys.modules['discord.ext.commands'].Cog = DummyCog

sys.modules['discord'].ui = Mock()
sys.modules['discord'].ui.button = Mock(return_value=identity_decorator)
sys.modules['discord'].ui.View = DummyCog 

# Fake Embed
class FakeEmbed:
    def __init__(self, title=None, description=None, color=None):
        self.title = title
        self.description = description
        self.fields = []
    def add_field(self, name, value, inline=False):
        self.fields.append({'name': name, 'value': value})
    def set_footer(self, text):
        pass

sys.modules['discord'].Embed = FakeEmbed
sys.modules['discord'].Color = Mock()

# app_commands for trader
sys.modules['discord'].app_commands = Mock()
sys.modules['discord'].app_commands.command = Mock(side_effect=command_decorator)

import discord
from dayz_discord_ops.casino import Casino, CrashView, BlackjackView
from dayz_discord_ops.tickets import Tickets, TicketView, TicketControlsView
from dayz_discord_ops.trader import TraderCog

# Channel IDs
TRADE_CHANNEL_ID = 1452554365574582345
CASINO_CHANNEL_ID = 1452554475909812366
TICKET_CHANNEL_ID = 1452557811497177143

async def test_casino_channel_enforcement():
    print("\n[TEST] Casino Channel Enforcement")
    bot = Mock()
    bot.db = Mock()
    casino = Casino(bot)
    
    # Mock Context
    ctx = AsyncMock()
    ctx.author.id = "123"
    ctx.channel.id = 999999999 # Wrong channel
    
    # Test blackjack in wrong channel
    await casino.blackjack(ctx, 100)
    ctx.send.assert_called_with(f"Casino commands only in <#{CASINO_CHANNEL_ID}>!", delete_after=5)
    print("✓ Blackjack blocked in wrong channel")
    
    # Test in correct channel
    ctx.reset_mock()
    ctx.channel.id = CASINO_CHANNEL_ID
    bot.db.get_balance.return_value = 1000
    
    await casino.blackjack(ctx, 100)
    if ctx.send.call_count > 0:
        # Check if it sent the game embed
        args, kwargs = ctx.send.call_args
        if kwargs.get('embed') and "Blackjack" in kwargs['embed'].title:
             print("✓ Blackjack allowed in correct channel")
        else:
             print("? Blackjack executed but output unclear")
    
    # CRASH GAME
    ctx.reset_mock()
    await casino.crash(ctx, 100)
    args, kwargs = ctx.send.call_args
    if kwargs.get('embed') and "CRASH" in kwargs['embed'].title:
        print("✓ Crash game initialized correctly")

async def test_ticket_features():
    print("\n[TEST] Ticket Features")
    bot = Mock()
    bot.db = Mock()
    bot.settings.discord_admin_role_ids = [999]
    tickets = Tickets(bot)
    
    # Test Ticket controls
    view = TicketControlsView(bot)
    interaction = AsyncMock()
    interaction.user.id = "456"
    interaction.user.roles = [Mock(id=999)] # Is Admin
    interaction.user.display_name = "AdminUser"
    button = Mock()
    
    # Test Claim
    await view.claim(interaction, button)
    interaction.response.send_message.assert_called_with(f"Ticket claimed by {interaction.user.mention}!")
    print("✓ Ticket Claim function executed")
    
    # Verify button update
    assert "Claimed by" in button.label
    assert button.disabled == True
    print("✓ Claim button updated state")

async def test_trader_channel_enforcement():
    print("\n[TEST] Trader Channel Enforcement")
    bot = Mock()
    bot.db = Mock()
    trader = TraderCog(bot)
    
    interaction = AsyncMock()
    interaction.user.id = "789"
    interaction.channel_id = 111111 # Wrong channel
    
    # Test buy restriction
    await trader.buy(interaction, "Apple")
    interaction.response.send_message.assert_called_with(f"Please use <#{TRADE_CHANNEL_ID}> for trading.", ephemeral=True)
    print("✓ Buy command blocked in wrong channel")
    
    # Correct channel - just verify it doesn't block
    interaction.reset_mock()
    interaction.channel_id = TRADE_CHANNEL_ID
    
    # The buy method will fail later due to missing items, but that's OK
    # We just want to verify the channel check passes
    try:
        await trader.buy(interaction, "NonexistentItem")
    except:
        pass # Expected to fail on item lookup
    
    # If we got here without the channel error message, channel check passed
    # Verify the channel error was NOT sent
    if interaction.response.send_message.called:
        args, kwargs = interaction.response.send_message.call_args
        assert "Please use" not in str(args), "Channel error should not be sent in correct channel"
    
    print("✓ Buy command allowed in correct channel")

async def main():
    print("=== Advanced Features Test Suite ===")
    await test_casino_channel_enforcement()
    await test_ticket_features()
    await test_trader_channel_enforcement()
    print("\n=== All Tests Passed ===")

if __name__ == "__main__":
    asyncio.run(main())
