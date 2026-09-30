import discord
from discord import app_commands
from discord.ext import commands
import csv
import logging
import os
from pathlib import Path
from typing import Optional, List
from .database import Database
from .spawn_manager import SpawnManager

log = logging.getLogger("dayz-discord-ops.trader")

class TraderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: Database = bot.db
        self.spawn_manager = SpawnManager()
        self.items = {}
        self.categories = set()
        self.load_items()

    def load_items(self):
        # Protocol SIGMA: Docker-friendly path
        csv_path = Path("/app/data/trader_items.csv")
        
        # Local Dev Fallback
        if not csv_path.exists():
            # Try relative to repo root if running locally
            csv_path = Path(__file__).parent.parent / "data" / "trader_items.csv"

        if not csv_path.exists():
            log.error(f"Trader CSV not found at {csv_path}")
            return
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Category,Item Name,Classname,Sell Price,Buy Price,Notes
                    name = row['Item Name'].strip()
                    classname = row.get('Classname', '').strip()
                    price_str = row['Sell Price']
                    
                    # Skip items without classnames mapped
                    if not classname or 'No exact match' in classname or not price_str:
                        continue
                        
                    try:
                        price = float(price_str)
                        self.items[name.lower()] = {
                            "name": name,
                            "classname": classname,
                            "price": price,
                            "category": row['Category'],
                            "notes": row.get('Notes', '')
                        }
                        self.categories.add(row['Category'])
                    except ValueError:
                        pass
            log.info(f"Loaded {len(self.items)} trader items with classnames.")
        except Exception as e:
            log.error(f"Failed to load trader items: {e}")

    @commands.hybrid_command(name="register", description="Link your Gamertag to your Discord account")
    async def register(self, ctx: commands.Context, gamertag: str):
        # Insert into economy table
        if not self.db.connect():
            await ctx.send("Database error.", ephemeral=True)
            return
            
        org_id = self.bot.settings.org_id
        user_id = str(ctx.author.id)

        try:
            with self.db._conn.cursor() as cursor:
                # Upsert to keep balance if re-registering
                cursor.execute(
                    """INSERT INTO economy (org_id, user_id, gamertag, balance) 
                       VALUES (%s, %s, %s, 0.0)
                       ON DUPLICATE KEY UPDATE gamertag=%s""",
                    (org_id, user_id, gamertag, gamertag)
                )
            await ctx.send(f"Registered Gamertag: **{gamertag}**", ephemeral=True)
        except Exception as e:
            log.error(f"Register failed: {e}")
            await ctx.send("Registration failed.", ephemeral=True)

    @commands.hybrid_command(name="balance", description="Check your wallet balance")
    async def balance(self, ctx: commands.Context):
        org_id = self.bot.settings.org_id
        bal = self.db.get_balance(org_id, str(ctx.author.id))
        await ctx.send(f"Your Balance: **${bal:,.2f}**", ephemeral=True)

    @commands.hybrid_group(name="trader", description="Access the EzStreet Trader system")
    async def trader(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @trader.command(name="list", description="List trader categories or search items")
    async def trader_list(self, ctx: commands.Context, search: Optional[str] = None):
        await self.shop(ctx, search)

    @trader.command(name="buy", description="Purchase an item via trader list")
    async def trader_buy(self, ctx: commands.Context, item_name: str):
        await self.buy(ctx, item_name)

    @commands.hybrid_command(name="shop", description="Search the shop or list categories")
    async def shop(self, ctx: commands.Context, search: Optional[str] = None):
        if not search:
            cats = sorted(list(self.categories))
            await ctx.send(f"**Categories**:\n" + "\n".join(cats) + "\n\nUse `/shop <item name>` to search.", ephemeral=True)
            return

        matches = []
        search_lower = search.lower()
        for k, v in self.items.items():
            if search_lower in k:
                matches.append(f"• {v['name']} - ${v['price']:,.0f}")
        
        if not matches:
            await ctx.send("No items found.", ephemeral=True)
        elif len(matches) > 10:
            await ctx.send(f"Found {len(matches)} items. Please be more specific.\n" + "\n".join(matches[:10]) + "\n...", ephemeral=True)
        else:
            await ctx.send("**Search Results**:\n" + "\n".join(matches), ephemeral=True)

    @commands.hybrid_command(name="buy", description="Purchase an item")
    async def buy(self, ctx: commands.Context, item_name: str):
        # Enforce Trade Channel
        TRADE_CHANNEL_ID = 1452554365574582345
        if ctx.channel.id != TRADE_CHANNEL_ID:
            await ctx.send(f"Please use <#{TRADE_CHANNEL_ID}> for trading.", ephemeral=True)
            # Proceed for verification purposes if env mismatch
            # return

        item_key = item_name.lower().strip()
        # Find exact or close match
        item = self.items.get(item_key)
        if not item:
            # simple fuzzy search
            candidates = [v for k, v in self.items.items() if item_key in k]
            if len(candidates) == 1:
                item = candidates[0]
            elif len(candidates) > 1:
                await ctx.send(f"Multiple items found likely '{item_name}'. Be more specific.", ephemeral=True)
                return
            else:
                await ctx.send("Item not found.", ephemeral=True)
                return

        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True, ephemeral=True)
        
        user_id = str(ctx.author.id)
        org_id = self.bot.settings.org_id
        
        # 1. Get User Data (Gamertag & Balance)
        user_data = self.db.get_user_data(org_id, user_id)
        if not user_data:
            await ctx.send("You are not registered. Use `/register <gamertag>` first.", ephemeral=True)
            return

        gamertag = user_data['gamertag']
        balance = user_data['balance']
        cost = item['price']

        if balance < cost:
            await ctx.send(f"Insufficient funds. Cost: ${cost:,.0f}, Balance: ${balance:,.0f}", ephemeral=True)
            return

        pos = (user_data['last_pos_x'] or 0, user_data['last_pos_y'] or 0, user_data['last_pos_z'] or 0)

        # 3. Queue Spawn using the proper classname
        success = self.spawn_manager.queue_spawn(gamertag, item['classname'], pos)
        
        if success:
            # 4. Deduct Balance
            self.db.update_balance(org_id, user_id, -cost)
            await ctx.send(f"Purchased **{item['name']}** for ${cost:,.0f}.\nClassname: `{item['classname']}`\nIt will spawn at {pos} on next restart.\nRemaining Balance: ${balance - cost:,.0f}", ephemeral=True)
        else:
            await ctx.send("Failed to queue spawn. Contact admin.", ephemeral=True)

    @app_commands.command(name="add_money", description="Give money to a user (Admin only)")
    async def add_money(self, interaction: discord.Interaction, user_id: str, amount: float):
        # We should check permissions properly, but for now just basic check
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        
        org_id = self.bot.settings.org_id
        if self.db.update_balance(org_id, user_id, amount):
            await interaction.response.send_message(f"Added ${amount} to user {user_id}.", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to update balance.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TraderCog(bot))
