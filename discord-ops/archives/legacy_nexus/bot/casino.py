import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

from .database import Database

class BlackjackView(discord.ui.View):
    def __init__(self, bot, user, bet):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.bet = bet
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(self.deck)
        self.player_hand = [self.deal(), self.deal()]
        self.dealer_hand = [self.deal(), self.deal()]
        self.finished = False

    def deal(self):
        return self.deck.pop()

    def score(self, hand):
        s = sum(hand)
        aces = hand.count(11)
        while s > 21 and aces:
            s -= 10
            aces -= 1
        return s

    async def update_message(self, interaction, result_msg=None):
        p_score = self.score(self.player_hand)
        d_score = self.score(self.dealer_hand)
        
        embed = discord.Embed(title="♠️ Blackjack ♥️", color=discord.Color.gold())
        embed.add_field(name=f"{self.user.display_name}'s Hand", value=f"{self.player_hand} (Score: {p_score})", inline=False)
        
        if self.finished:
            embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand} (Score: {d_score})", inline=False)
            embed.description = result_msg
        else:
            embed.add_field(name="Dealer's Hand", value=f"[{self.dealer_hand[0]}, ?]", inline=False)
            embed.description = "Hit or Stand?"

        await interaction.response.edit_message(embed=embed, view=self if not self.finished else None)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        self.player_hand.append(self.deal())
        if self.score(self.player_hand) > 21:
            self.finished = True
            await self.finish_game(interaction, "Bust! You lose.", win=False)
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        self.finished = True
        
        # Dealer turn
        while self.score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deal())
            
        p_score = self.score(self.player_hand)
        d_score = self.score(self.dealer_hand)
        
        if d_score > 21:
            await self.finish_game(interaction, "Dealer Bust! You win!", win=True)
        elif p_score > d_score:
            await self.finish_game(interaction, "You have higher score! You win!", win=True)
        elif p_score < d_score:
            await self.finish_game(interaction, "Dealer has higher score. You lose.", win=False)
        else:
            await self.finish_game(interaction, "Push! Money returned.", win=None)

    async def finish_game(self, interaction, msg, win):
        db = self.bot.db
        if win is True:
            db.update_balance(str(self.user.id), self.bet * 2) 
            msg += f"\nWon {self.bet}!"
        elif win is False:
             pass # Already deducted
             msg += f"\nLost {self.bet}."
        else:
            db.update_balance(str(self.user.id), self.bet)
            msg += "\nBet returned."
            
        await self.update_message(interaction, msg)
        self.stop()

class CrashView(discord.ui.View):
    def __init__(self, bot, user, bet):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.bet = bet
        self.multiplier = 1.00
        self.crashed = False
        self.cashed_out = False
        self.task = None

    async def start_game(self, interaction):
        self.message = await interaction.original_response()
        self.task = asyncio.create_task(self.run_crash())

    async def run_crash(self):
        try:
            while not self.crashed and not self.cashed_out:
                await asyncio.sleep(2.0 if self.multiplier == 1.0 else 1.0) # Start slow
                
                # Crash chance logic
                # 1% instant crash at 1.00x
                # Then increasing chance? 
                # Simple logic: 4% chance to crash every tick?
                # Or generate crash point at start.
                if self.multiplier == 1.00 and random.random() < 0.05:
                     self.crashed = True
                     break
                
                if random.random() < 0.1: # 10% chance to crash each tick
                    self.crashed = True
                    break
                    
                self.multiplier += 0.2 + (random.random() * 0.3)
                
                # Update visual
                embed = discord.Embed(title="🚀 CRASH 🚀", description=f"Multiplier: **{self.multiplier:.2f}x**", color=discord.Color.blue())
                embed.add_field(name="Your Bet", value=f"{self.bet}")
                await self.message.edit(embed=embed, view=self)
            
            if self.crashed:
                await self.end_game(False)
                
        except asyncio.CancelledError:
            pass

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.success)
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        if self.crashed or self.cashed_out: return
        
        self.cashed_out = True
        if self.task: self.task.cancel()
        await self.end_game(True, interaction)

    async def end_game(self, win, interaction=None):
        if interaction:
             # If invoked by button
             pass
        
        embed = discord.Embed(title="🚀 CRASH 🚀", color=discord.Color.green() if win else discord.Color.red())
        if win:
            winnings = self.bet * self.multiplier
            self.bot.db.update_balance(str(self.user.id), winnings)
            embed.description = f"Cashed out at **{self.multiplier:.2f}x**! Won **${winnings:,.0f}**"
        else:
            embed.description = f"CRASHED at **{self.multiplier:.2f}x**. You lost **${self.bet:,.0f}**."
        
        # Disable buttons
        for child in self.children:
            child.disabled = True
            
        if self.message:
            await self.message.edit(embed=embed, view=self)

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1452554475909812366

    async def check_channel(self, ctx):
        if ctx.channel.id != self.channel_id:
            await ctx.send(f"Casino commands only in <#{self.channel_id}>!", delete_after=5)
            return False
        return True

    @commands.hybrid_command(name="blackjack", aliases=["bj"], description="Play a game of Blackjack")
    @app_commands.describe(bet="Amount of coins to bet")
    async def blackjack(self, ctx: commands.Context, bet: float):
        if not await self.check_channel(ctx): return
        if bet <= 0: return await ctx.send("Bet must be positive.")
        
        bal = self.bot.db.get_balance(str(ctx.author.id))
        if bal < bet:
            return await ctx.send(f"Insufficient funds. Balance: {bal}")
            
        self.bot.db.update_balance(str(ctx.author.id), -bet)
        
        view = BlackjackView(self.bot, ctx.author, bet)
        embed = discord.Embed(title="♠️ Blackjack ♥️", description=f"Bet: {bet}", color=discord.Color.gold())
        embed.set_footer(text="Initializing...")
        
        msg = await ctx.send(embed=embed, view=view)
        # Mock initial interaction for update
        class MockInteraction:
            def __init__(self, msg): self.message = msg
            response = type('Response', (), {'edit_message': lambda self, embed, view: msg.edit(embed=embed, view=view)})()
        
        await view.update_message(MockInteraction(msg))

    @commands.hybrid_command(name="crash", description="Play a game of Crash (Rocket Multiplier)")
    @app_commands.describe(bet="Amount of coins to bet")
    async def crash(self, ctx: commands.Context, bet: float):
        if not await self.check_channel(ctx): return
        if bet <= 0: return await ctx.send("Bet must be positive.")
        
        bal = self.bot.db.get_balance(str(ctx.author.id))
        if bal < bet:
            return await ctx.send(f"Insufficient funds. Balance: {bal}")
            
        self.bot.db.update_balance(str(ctx.author.id), -bet)
        
        view = CrashView(self.bot, ctx.author, bet)
        embed = discord.Embed(title="🚀 CRASH 🚀", description="Preparing launch...", color=discord.Color.blue())
        
        interaction = await ctx.send(embed=embed, view=view)
        # Need interaction object to edit? No, view stores message.
        # Wait, start_game needs interaction to get original_response for message?
        # Actually ctx.send returns message.
        
        # Let's fix View start
        view.message = interaction
        view.task = asyncio.create_task(view.run_crash())

    @commands.hybrid_command(name="slots", description="Play the Slot Machine")
    @app_commands.describe(bet="Amount of coins to bet")
    async def slots(self, ctx: commands.Context, bet: float):
        if not await self.check_channel(ctx): return
        if bet <= 0: return await ctx.send("Bet must be positive.")
        bal = self.bot.db.get_balance(str(ctx.author.id))
        if bal < bet:
            return await ctx.send(f"Insufficient funds. Balance: {bal}")
        
        self.bot.db.update_balance(str(ctx.author.id), -bet)
        
        emojis = ["🍒", "🍋", "🍇", "🍉", "🔔", "💎", "7️⃣"]
        a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
        
        result = f"{a} | {b} | {c}"
        embed = discord.Embed(title="🎰 Slots 🎰", description=result, color=discord.Color.purple())
        
        win_mult = 0
        if a == b == c:
            win_mult = 10
            if a == "7️⃣": win_mult = 50
            if a == "💎": win_mult = 25
        elif a == b or b == c or a == c:
            win_mult = 2
            
        if win_mult > 0:
            winnings = bet * win_mult
            self.bot.db.update_balance(str(ctx.author.id), winnings)
            embed.add_field(name="Winner!", value=f"You won {winnings} ({win_mult}x)!")
        else:
            embed.add_field(name="Loser!", value="Better luck next time.")
            
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="roulette", description="Play a game of Roulette")
    @app_commands.describe(bet="Amount of coins to bet", choice="Color (red, black, green) or Number (0-36)")
    async def roulette(self, ctx: commands.Context, bet: float, choice: str):
        if not await self.check_channel(ctx): return
        if bet <= 0: return await ctx.send("Bet must be positive.")
        bal = self.bot.db.get_balance(str(ctx.author.id))
        if bal < bet:
            return await ctx.send(f"Insufficient funds. Balance: {bal}")

        self.bot.db.update_balance(str(ctx.author.id), -bet)
        
        choice = choice.lower()
        if choice not in ["red", "black", "green"] and not choice.isdigit():
             self.bot.db.update_balance(str(ctx.author.id), bet) # refund
             return await ctx.send("Invalid choice. Choose: red, black, green, or a number 0-36.")

        number = random.randint(0, 36)
        
        reds = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        if number == 0: color = "green"
        elif number in reds: color = "red"
        else: color = "black"
        
        winnings = 0
        won = False
        
        if choice.isdigit():
            if int(choice) == number:
                winnings = bet * 35
                won = True
        elif choice == color:
            winnings = bet * 2
            if choice == "green": winnings = bet * 14
            won = True
            
        embed = discord.Embed(title="🎡 Roulette 🎡", color=discord.Color.red() if color=="red" else discord.Color.dark_grey())
        embed.description = f"Ball landed on: **{number} ({color.upper()})**"
        
        if won:
            self.bot.db.update_balance(str(ctx.author.id), winnings)
            embed.add_field(name="Result", value=f"You WIN {winnings}!")
        else:
            embed.add_field(name="Result", value="You Lose.")
            
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(self.bot.settings.discord_guild_id)
        if not guild: return
        
        # Get specific casino channel
        channel = guild.get_channel(self.channel_id)
        if channel:
             # Check if last message was from bot, if not, post welcome
             # Or just post purely
             pass
        else:
            print(f"Casino channel {self.channel_id} not found!")

async def setup(bot):
    await bot.add_cog(Casino(bot))
# Auto-reload test 1766858941

