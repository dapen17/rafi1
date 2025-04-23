import asyncio
import re
import logging
from telethon import events, errors
from telethon.tl.types import InputPeerUser
from datetime import datetime
from collections import defaultdict

# Menonaktifkan logging Telethon
logging.basicConfig(level=logging.CRITICAL)

# Menyimpan status per akun dan grup
active_groups = defaultdict(lambda: defaultdict(bool))  # {group_id: {user_id: status}}
active_bc_interval = defaultdict(lambda: defaultdict(bool))  # {user_id: {type: status}}
blacklist = set()
auto_replies = defaultdict(str)  # {user_id: auto_reply_message}

def parse_interval(interval_str):
    match = re.match(r'^(\d+)([smhd])$', interval_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    return value * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

async def configure_event_handlers(client, user_id):

    # Spam pesan ke grup
    @client.on(events.NewMessage(pattern=r'^ary hastle (.+) (\d+[smhd])$'))
    async def hastle_handler(event):
        custom_message, interval_str = event.pattern_match.groups()
        group_id = event.chat_id
        interval = parse_interval(interval_str)

        if not interval:
            await event.reply("⚠️ Format waktu salah! Gunakan format 10s, 1m, 2h, dll.")
            return

        if active_groups[group_id][user_id]:
            await event.reply("⚠️ Spam sudah berjalan untuk akun Anda di grup ini.")
            return

        active_groups[group_id][user_id] = True
        await event.reply(f"✅ Memulai spam: {custom_message} setiap {interval_str} untuk akun Anda.")
        while active_groups[group_id][user_id]:
            try:
                await client.send_message(group_id, custom_message)
                await asyncio.sleep(interval)
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception:
                active_groups[group_id][user_id] = False

    # Hentikan spam
    @client.on(events.NewMessage(pattern=r'^ary stop$'))
    async def stop_handler(event):
        group_id = event.chat_id
        if active_groups[group_id][user_id]:
            active_groups[group_id][user_id] = False
            await event.reply("✅ Spam dihentikan.")
        else:
            await event.reply("⚠️ Tidak ada spam yang berjalan.")

    # Tes koneksi
    @client.on(events.NewMessage(pattern=r'^ary ping$'))
    async def ping_handler(event):
        await event.reply("🏓 Pong! Bot aktif.")

    # Broadcast ke semua chat (multi-line)
    @client.on(events.NewMessage(pattern=r'^ary bcstar\s+([\s\S]+)', flags=re.DOTALL))
    async def broadcast_handler(event):
        custom_message = event.pattern_match.group(1).strip()
        await event.reply(f"✅ Memulai broadcast ke semua chat:\n\n{custom_message}")
        async for dialog in client.iter_dialogs():
            if dialog.id in blacklist:
                continue
            try:
                await client.send_message(dialog.id, custom_message)
            except Exception:
                pass

    # Broadcast ke grup dengan interval (multi-line)
    @client.on(events.NewMessage(pattern=r'^ary bcstargr(\d+)\s+(\d+[smhd])\s+([\s\S]+)', flags=re.DOTALL))
    async def broadcast_group_handler(event):
        group_number = event.pattern_match.group(1)
        interval_str = event.pattern_match.group(2)
        custom_message = event.pattern_match.group(3).strip()
        interval = parse_interval(interval_str)

        if not interval:
            await event.reply("⚠️ Format waktu salah! Gunakan format 10s, 1m, 2h, dll.")
            return

        if active_bc_interval[user_id][f"group{group_number}"]:
            await event.reply(f"⚠️ Broadcast ke grup {group_number} sudah berjalan.")
            return

        active_bc_interval[user_id][f"group{group_number}"] = True
        await event.reply(f"✅ Memulai broadcast ke grup {group_number} dengan interval {interval_str}:\n\n{custom_message}")
        while active_bc_interval[user_id][f"group{group_number}"]:
            async for dialog in client.iter_dialogs():
                if dialog.is_group and dialog.id not in blacklist:
                    try:
                        await client.send_message(dialog.id, custom_message)
                    except Exception:
                        pass
            await asyncio.sleep(interval)

    # Hentikan broadcast grup
    @client.on(events.NewMessage(pattern=r'^ary stopbcstargr(\d+)$'))
    async def stop_broadcast_group_handler(event):
        group_number = event.pattern_match.group(1)
        if active_bc_interval[user_id][f"group{group_number}"]:
            active_bc_interval[user_id][f"group{group_number}"] = False
            await event.reply(f"✅ Broadcast ke grup {group_number} dihentikan.")
        else:
            await event.reply(f"⚠️ Tidak ada broadcast grup {group_number} yang berjalan.")

    # Blacklist chat
    @client.on(events.NewMessage(pattern=r'^ary bl$'))
    async def blacklist_handler(event):
        chat_id = event.chat_id
        blacklist.add(chat_id)
        await event.reply("✅ Grup ini telah ditambahkan ke blacklist.")

    # Unblacklist chat
    @client.on(events.NewMessage(pattern=r'^ary unbl$'))
    async def unblacklist_handler(event):
        chat_id = event.chat_id
        if chat_id in blacklist:
            blacklist.remove(chat_id)
            await event.reply("✅ Grup ini telah dihapus dari blacklist.")
        else:
            await event.reply("⚠️ Grup ini tidak ada dalam blacklist.")

    # Bantuan
    @client.on(events.NewMessage(pattern=r'^ary help$'))
    async def help_handler(event):
        help_text = (
            "📋 **Daftar Perintah yang Tersedia:**\n\n"
            "1. ary hastle [pesan] [waktu][s/m/h/d]\n"
            "   Spam pesan ke grup.\n"
            "2. ary stop\n"
            "   Hentikan spam.\n"
            "3. ary ping\n"
            "   Cek status bot.\n"
            "4. ary bcstar [pesan multi-baris]\n"
            "   Broadcast ke semua chat.\n"
            "5. ary bcstargr[n] [waktu][s/m/h/d] [pesan multi-baris]\n"
            "   Broadcast ke grup dengan interval.\n"
            "6. ary stopbcstargr[n]\n"
            "   Stop broadcast grup.\n"
            "7. ary bl / ary unbl\n"
            "   Tambah / Hapus dari blacklist.\n"
            "8. ary setreply [pesan multi-baris]\n"
            "   Atur auto-reply.\n"
            "9. ary stopall\n"
            "   Reset semua pengaturan."
        )
        await event.reply(help_text)

    # Set auto-reply (multi-line)
    @client.on(events.NewMessage(pattern=r'^ary setreply\s+([\s\S]+)', flags=re.DOTALL))
    async def set_auto_reply(event):
        reply_message = event.pattern_match.group(1).strip()
        auto_replies[user_id] = reply_message
        await event.reply(f"\u2705 Auto-reply diatur:\n\n{reply_message}")

    # Auto-reply saat pesan masuk
    @client.on(events.NewMessage(incoming=True))
    async def auto_reply_handler(event):
        if event.is_private and user_id in auto_replies and auto_replies[user_id]:
            try:
                sender = await event.get_sender()
                peer = InputPeerUser(sender.id, sender.access_hash)
                await client.send_message(peer, auto_replies[user_id])
                await client.send_read_acknowledge(peer)
            except Exception:
                pass

    # Reset semua
    @client.on(events.NewMessage(pattern=r'^ary stopall$'))
    async def stop_all_handler(event):
        for group_key in active_bc_interval[user_id].keys():
            active_bc_interval[user_id][group_key] = False
        auto_replies[user_id] = ""
        blacklist.clear()
        for group_id in active_groups.keys():
            active_groups[group_id][user_id] = False
        await event.reply("\u2705 Semua pengaturan telah direset.")
