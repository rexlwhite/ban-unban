import discord, re, os
from discord.ext import commands
from datetime import datetime
from threading import Thread
from flask import Flask

# ==========================================
# ระบบเว็บเซิร์ฟเวอร์เพื่อป้องกัน Render ดับ
# ==========================================
app = Flask('')

@app.route('/')
def home(): 
    return "Bot is online"

def run_web(): 
    app.run(host='0.0.0.0', port=10000)

# ==========================================
# ระบบบอท DISCORD MAIN CODE
# ==========================================
intents = discord.Intents.default()
intents.members = intents.message_content = True

def get_prefix(bot, message): 
    return bot.custom_prefix

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.custom_prefix = "!"

cfg = {
    "title": "สมาชิกถูกแบน", 
    "desc": "", 
    "color": 16711680, 
    "thumb": "user", 
    "url": "", 
    "main_image": "", 
    "u_t": "ผู้ถูกลงโทษ", 
    "m_t": "ผู้ลงทัณฑ์", 
    "r_t": "เหตุผล"
}

@bot.event
async def on_ready():
    print(f'Ready: {bot.user.name}')
    await bot.tree.sync()

async def get_user(guild, val, is_ban=False):
    val = val.strip()
    m = re.match(r'<@!?(\d+)>', val)
    uid = int(m.group(1)) if m else (int(val) if val.isdigit() else None)
    if is_ban:
        async for b in guild.bans():
            if (uid and b.user.id == uid) or val in (b.user.name, f"{b.user.name}#{b.user.discriminator}"): 
                return b.user
        if uid:
            try: return await bot.fetch_user(uid)
            except: return None
    else:
        u = discord.utils.get(guild.members, name=val) or discord.utils.get(guild.members, name=val.split('#'))
        if u: return u
        if uid:
            try: return await bot.fetch_user(uid)
            except: return None
    return None

def make_embed(u, mod, r=None, is_dm=False, is_un=False):
    emb = discord.Embed(
        title="คุณถูกแบน" if is_dm else ("ปลดแบนสมาชิก" if is_un else cfg["title"]), 
        color=discord.Color.green() if is_un else discord.Color(cfg["color"]), 
        timestamp=datetime.utcnow()
    )
    if cfg["desc"] and not is_un: 
        emb.description = cfg["desc"]
    emb.set_thumbnail(url=u.display_avatar.url if cfg["thumb"] == "user" or not cfg["url"] else cfg["url"])
    if cfg["main_image"] and not is_un: 
        emb.set_image(url=cfg["main_image"])

    if is_un:
        emb.add_field(name="ผู้ได้รับอิสรภาพ", value=f"{u.mention}\nID: {u.id}").add_field(name="ผู้ปลดบล็อค", value=mod.mention)
    else:
        emb.add_field(name=cfg["u_t"], value=f"{u.mention}\nID: {u.id}").add_field(name=cfg["m_t"], value=mod.mention)
        emb.add_field(name=cfg["r_t"], value=r or "ไม่ได้ระบุเหตุผล", inline=False)
    return emb

async def do_ban(ctx_or_int, guild, sender, val, r):
    u = await get_user(guild, val)
    if not u: 
        return await (ctx_or_int.send('ไม่พบผู้ใช้') if hasattr(ctx_or_int, 'send') else ctx_or_int.response.send_message('ไม่พบผู้ใช้', ephemeral=True))
    try:
        try: await u.send(embed=make_embed(u, sender, r, is_dm=True))
        except: pass
        await guild.ban(u, reason=r)
        await (ctx_or_int.send(embed=make_embed(u, sender, r)) if hasattr(ctx_or_int, 'send') else ctx_or_int.response.send_message(embed=make_embed(u, sender, r)))
    except: 
        await (ctx_or_int.send('ไม่มีสิทธิ์แบน') if hasattr(ctx_or_int, 'send') else ctx_or_int.response.send_message('ไม่มีสิทธิ์แบน', ephemeral=True))

async def do_unban(ctx_or_int, guild, sender, val):
    u = await get_user(guild, val, is_ban=True)
    if not u: 
        return await (ctx_or_int.send('ไม่พบผู้ใช้ในรายการแบน') if hasattr(ctx_or_int, 'send') else ctx_or_int.response.send_message('ไม่พบผู้ใช้ในรายการแบน', ephemeral=True))
    try:
        await guild.unban(u)
        await (ctx_or_int.send(embed=make_embed(u, sender, is_un=True)) if hasattr(ctx_or_int, 'send') else ctx_or_int.response.send_message(embed=make_embed(u, sender, is_un=True)))
    except: 
        await (ctx_or_int.send('ไม่สามารถปลดแบนได้') if hasattr(ctx_or_int, 'send') else ctx_or_int.response.send_message('ไม่สามารถปลดแบนได้', ephemeral=True))

@bot.command(name='ban', aliases=['b'])
@commands.has_permissions(ban_members=True)
async def p_ban(ctx, val: str = None, *, r=None):
    if not val: 
        return await ctx.send("กรุณากรอกข้อมูลให้ครบถ้วน")
    await do_ban(ctx, ctx.guild, ctx.author, val, r)

@bot.command(name='unban')
@commands.has_permissions(ban_members=True)
async def p_unban(ctx, *, val: str = None):
    if not val: 
        return await ctx.send("กรุณากรอกข้อมูลให้ครบถ้วน")
    await do_unban(ctx, ctx.guild, ctx.author, val)

@bot.tree.command(name='ban')
@discord.app_commands.checks.has_permissions(ban_members=True)
async def s_ban(i: discord.Interaction, user_input: str, reason: str = None): 
    await do_ban(i, i.guild, i.user, user_input, reason)

@bot.tree.command(name='unban')
@discord.app_commands.checks.has_permissions(ban_members=True)
async def s_unban(i: discord.Interaction, user_input: str): 
    await do_unban(i, i.guild, i.user, user_input)

class PModal(discord.ui.Modal, title='เปลี่ยน Prefix'):
    p_input = discord.ui.TextInput(label='ระบุ Prefix ใหม่ (เช่น ? หรือ .)', max_length=5)
    async def on_submit(self, i: discord.Interaction):
        bot.custom_prefix = self.p_input.value
        await i.response.send_message(f"เปลี่ยน Prefix เป็น `{bot.custom_prefix}` เรียบร้อยแล้ว", ephemeral=True)

class TModal(discord.ui.Modal, title='แก้ไขข้อความและคำอธิบาย'):
    t = discord.ui.TextInput(label='หัวข้อหลัก', default=cfg["title"])
    d = discord.ui.TextInput(label='คำอธิบายเพิ่มเติม (Description)', default=cfg["desc"], required=False, style=discord.TextStyle.paragraph)
    u = discord.ui.TextInput(label='ช่องผู้โดนแบน', default=cfg["u_t"])
    m = discord.ui.TextInput(label='ช่องผู้ลงโทษ', default=cfg["m_t"])
    r = discord.ui.TextInput(label='ช่องเหตุผล', default=cfg["r_t"])
    async def on_submit(self, i: discord.Interaction):
        cfg["title"], cfg["desc"], cfg["u_t"], cfg["m_t"], cfg["r_t"] = self.t.value, self.d.value, self.u.value, self.m.value, self.r.value
        await i.response.send_message("บันทึกคำและคำอธิบายแล้ว", ephemeral=True)

class SModal(discord.ui.Modal, title='แก้ไขสไตล์และรูปภาพ'):
    c = discord.ui.TextInput(label='สี Hex (เช่น ff0000 หรือ สีแดง)', default='สีแดง')
    img = discord.ui.TextInput(label='ลิงก์รูปขวาบน (เว้นว่าง=ใช้รูปโปรไฟล์)', required=False)
    m_img = discord.ui.TextInput(label='ลิงก์รูปภาพใหญ่ด้านล่างการ์ด', required=False)
    async def on_submit(self, i: discord.Interaction):
        v = self.c.value.strip().replace("#", "")
        cfg["color"] = 16711680 if v in ("สีแดง", "red") else (255 if v in ("สีฟ้า", "blue") else (0 if v == "สีดำ" else int(v, 16)))
        cfg["thumb"], cfg["url"] = ("custom", self.img.value) if self.img.value else ("user", "")
        cfg["main_image"] = self.m_img.value
        await i.response.send_message("บันทึกสไตล์และรูปภาพแล้ว", ephemeral=True)

class CView(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)

    @discord.ui.button(label="แก้ไขข้อความ & คำอธิบาย", style=discord.ButtonStyle.primary, custom_id="c_txt", row=0)
    async def e_txt(self, i: discord.Interaction, b): 
        await i.response.send_modal(TModal())

    @discord.ui.button(label="แก้ไขสี & รูปภาพทั้งหมด", style=discord.ButtonStyle.secondary, custom_id="c_sty", row=1)
    async def e_sty(self, i: discord.Interaction, b): 
        await i.response.send_modal(SModal())

    @discord.ui.button(label="เปลี่ยน Prefix บอท", style=discord.ButtonStyle.success, custom_id="c_pfx", row=2)
    async def e_pfx(self, i: discord.Interaction, b): 
        await i.response.send_modal(PModal())

@bot.tree.command(name='settings', description='เปิดศูนย์ควบคุมเพื่อตั้งค่า Prefix และ Embed บอท')
@discord.app_commands.checks.has_permissions(administrator=True)
async def open_settings(i: discord.Interaction):
    embed = discord.Embed(title="ศูนย์ควบคุมและตั้งค่าบอท", description=f"Prefix ปัจจุบันของบอทคือ: `{bot.custom_prefix}`\n\n**กรุณาเลือกปุ่มด้านล่างเพื่อแก้คำอธิบาย รูปภาพ และสไตล์การแบนได้ทันที:**", color=discord.Color.orange())
    await i.response.send_message(embed=embed, view=CView())

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument): 
        await ctx.send("กรุณากรอกข้อมูลให้ครบถ้วน")
    elif isinstance(error, commands.MissingPermissions): 
        await ctx.send("ข้อผิดพลาด: คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(os.getenv('TOKEN'))
