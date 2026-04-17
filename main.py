import discord
from discord.ext import commands
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import io
import os
from git import Repo # Added for GitHub Sync

# --- CONFIGURATION ---
TOKEN = 'MTQ5MzgyMzg0NjEzNzIwNDc2Nw.GVQlS2.jj0-hblwuC0FLekv_i46cCmHznJarr-wGlUfGk' # PLEASE RESET YOUR TOKEN IN DEVELOPER PORTAL
PATH_TO_REPO = r'C:\Users\canet\OneDrive\Desktop\MyBot'

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def init_db():
    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats 
                 (date TEXT PRIMARY KEY, msgs INTEGER, joins INTEGER, leaves INTEGER, 
                  total_mems INTEGER, unique_users TEXT)''')
    conn.commit()
    conn.close()

def export_to_csv_and_sync():
    """Extracts data from DB, writes to CSVs, and pushes to GitHub"""
    try:
        conn = sqlite3.connect('analytics.db')
        c = conn.cursor()
        c.execute("SELECT date, msgs, unique_users, total_mems FROM daily_stats ORDER BY date ASC")
        rows = c.fetchall()
        conn.close()

        # Prepare the data lines
        msg_lines = []
        mem_lines = []
        unq_lines = []

        for row in rows:
            date_str = row[0]
            msg_count = row[1]
            # Calculate unique count from the comma-separated string
            try:
                unique_count = len([u for u in row[2].split(',') if u])
            except:
                unique_count = row[2] if row[2] else 0
            total_mems = row[3] if row[3] else 0

            msg_lines.append(f"{date_str},{msg_count}\n")
            mem_lines.append(f"{date_str},{total_mems}\n")
            unq_lines.append(f"{date_str},{unique_count}\n")

        # Write to the CSV files (Overwrites with fresh full history)
        with open(os.path.join(PATH_TO_REPO, 'total_messages.csv'), 'w') as f: f.writelines(msg_lines)
        with open(os.path.join(PATH_TO_REPO, 'total_members.csv'), 'w') as f: f.writelines(mem_lines)
        with open(os.path.join(PATH_TO_REPO, 'message_stats.csv'), 'w') as f: f.writelines(unq_lines)

        # Sync to GitHub
        repo = Repo(PATH_TO_REPO)
        repo.index.add(['message_stats.csv', 'total_members.csv', 'total_messages.csv'])
        repo.index.commit(f"Auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        repo.remotes.origin.push('main')
        print("✅ GitHub Sync Complete")

    except Exception as e:
        print(f"❌ Sync Error: {e}")

def update_db(date, msgs=0, joins=0, leaves=0, total=None):
    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO daily_stats VALUES (?, 0, 0, 0, 0, '')", (date,))
    if msgs: c.execute("UPDATE daily_stats SET msgs = msgs + ? WHERE date = ?", (msgs, date))
    if joins: c.execute("UPDATE daily_stats SET joins = joins + ? WHERE date = ?", (joins, date))
    if leaves: c.execute("UPDATE daily_stats SET leaves = leaves + ? WHERE date = ?", (leaves, date))
    if total: c.execute("UPDATE daily_stats SET total_mems = ? WHERE date = ?", (total, date))
    conn.commit()
    conn.close()
    # Trigger export and sync
    export_to_csv_and_sync()

@bot.event
async def on_ready():
    init_db()
    print(f'Bot is online as {bot.user}')

@bot.event
async def on_member_join(member):
    today = datetime.now().strftime('%Y-%m-%d')
    update_db(today, joins=1, total=member.guild.member_count)

@bot.event
async def on_member_remove(member):
    today = datetime.now().strftime('%Y-%m-%d')
    update_db(today, leaves=1, total=member.guild.member_count)

@bot.event
async def on_message(message):
    if message.author.bot: return
    today = datetime.now().strftime('%Y-%m-%d')
    update_db(today, msgs=1, total=message.guild.member_count)
    
    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()
    c.execute("SELECT unique_users FROM daily_stats WHERE date = ?", (today,))
    result = c.fetchone()
    users_str = result[0] if result else ""
    users_list = users_str.split(',') if users_str else []
    
    if str(message.author.id) not in users_list:
        users_list.append(str(message.author.id))
        c.execute("UPDATE daily_stats SET unique_users = ? WHERE date = ?", (','.join(users_list), today))
        conn.commit()
    conn.close()
    
    await bot.process_commands(message)

# ... (Rest of your commands like !stats and !chart stay the same)
@bot.command()
async def stats(ctx):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()
    c.execute("SELECT msgs, unique_users, joins, leaves, total_mems FROM daily_stats WHERE date = ?", (today,))
    row = c.fetchone()
    conn.close()
    
    if row:
        try:
            unique_count = len([u for u in row[1].split(',') if u])
        except:
            unique_count = row[1] if row[1] else 0

        msg = (f"**Today's Stats ({today}):**\n"
               f"💬 Messages: {row[0]}\n"
               f"👥 Unique Chatters: {unique_count}\n"
               f"📥 Joins: {row[2]}\n"
               f"📤 Leaves: {row[3]}\n"
               f"📊 Total Members: {row[4] if row[4] else ctx.guild.member_count}")
        await ctx.send(msg)

@bot.command()
async def chart(ctx):
    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()
    c.execute("SELECT date, msgs, joins FROM daily_stats ORDER BY date ASC")
    data = c.fetchall()
    conn.close()

    if not data:
        await ctx.send("No data yet!")
        return

    dates = [row[0][5:] for row in data] 
    msgs = [row[1] for row in data]
    joins = [row[2] for row in data]

    plt.style.use('dark_background')
    dynamic_width = max(10, len(dates) * 0.3)
    fig, ax1 = plt.subplots(figsize=(dynamic_width, 5))

    ax1.bar(dates, msgs, color='#2ecc71', alpha=0.6, label='Messages')
    ax1.set_ylabel('Messages', color='#2ecc71')
    
    ax2 = ax1.twinx()
    ax2.plot(dates, joins, color='#3498db', marker='o', markersize=4, linewidth=2, label='Joins')
    ax2.set_ylabel('Joins', color='#3498db')

    plt.title(f'Server History ({len(dates)} Days)')
    fig.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    await ctx.send(file=discord.File(buf, 'chart.png'))
bot.run(TOKEN)