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
    """Konversi format [10s, 1m, 2h, 1d] menjadi detik."""
    match = re.match(r'^(\d+)([smhd])$', interval_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    return value * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]

def get_today_date():
    """Mengembalikan tanggal hari ini dalam format YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")

async def configure_event_handlers(client, user_id):
    """Konfigurasi semua fitur bot untuk user_id tertentu."""

    # Spam pesan ke grup dengan interval tertentu
    @client.on(events.NewMessage(pattern=r'^gal hastle (.+) (\d+[smhd])$'))
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
            except Exception as e:
                # Menangani error tanpa output log
                active_groups[group_id][user_id] = False

    # Hentikan spam di grup
    @client.on(events.NewMessage(pattern=r'^gal stop$'))
    async def stop_handler(event):
        group_id = event.chat_id
        if active_groups[group_id][user_id]:
            active_groups[group_id][user_id] = False
            await event.reply("✅ Spam dihentikan untuk akun Anda di grup ini.")
        else:
            await event.reply("⚠️ Tidak ada spam yang berjalan untuk akun Anda di grup ini.")

    # Tes koneksi bot
    @client.on(events.NewMessage(pattern=r'^gal ping$'))
    async def ping_handler(event):
        await event.reply("🏓 Pong! Bot aktif.")

    # Broadcast pesan ke semua chat kecuali blacklist
    @client.on(events.NewMessage(pattern=r'^gal bcstar (.+)$'))
    async def broadcast_handler(event):
        custom_message = event.pattern_match.group(1)
        await event.reply(f"✅ Memulai broadcast ke semua chat: {custom_message}")
        async for dialog in client.iter_dialogs():
            if dialog.id in blacklist:
                continue
            try:
                await client.send_message(dialog.id, custom_message)
            except Exception as e:
                # Menangani error tanpa output log
                pass

    # Broadcast pesan hanya ke grup dengan interval tertentu
    @client.on(events.NewMessage(pattern=r'^gal bcstargr(\d+) (\d+[smhd]) (.+)$'))
    async def broadcast_group_handler(event):
        group_number = event.pattern_match.group(1)
        interval_str, custom_message = event.pattern_match.groups()[1:]
        interval = parse_interval(interval_str)

        if not interval:
            await event.reply("⚠️ Format waktu salah! Gunakan format 10s, 1m, 2h, dll.")
            return

        if active_bc_interval[user_id][f"group{group_number}"]:
            await event.reply(f"⚠️ Broadcast ke grup {group_number} sudah berjalan.")
            return

        active_bc_interval[user_id][f"group{group_number}"] = True
        await event.reply(f"✅ Memulai broadcast ke grup {group_number} dengan interval {interval_str}: {custom_message}")
        while active_bc_interval[user_id][f"group{group_number}"]:
            async for dialog in client.iter_dialogs():
                if dialog.is_group and dialog.id not in blacklist:
                    try:
                        await client.send_message(dialog.id, custom_message)
                    except Exception as e:
                        # Menangani error tanpa output log
                        pass
            await asyncio.sleep(interval)

        from collections import defaultdict
    import asyncio
    import re

    # Menyimpan state pesan yang akan disebarkan
    broadcast_messages = defaultdict(lambda: defaultdict(lambda: None))  # {user_id: {tag: message}}

    # Counter untuk tag broadcast
    broadcast_counter = defaultdict(lambda: 1)  # {user_id: next_tag_number}

    @client.on(events.NewMessage(pattern=r'^gal jasebtime(\d+) (\d+[smhd]) (\d+[smhd]|1week|1month)$'))
    async def jasebtime_handler(event):
        lines = event.raw_text.split('\n', 1)
        match = re.match(r'^gal jasebtime(\d+) (\d+[smhd]) (\d+[smhd]|1week|1month)', lines[0])

        if not match or len(lines) < 2:
            await event.reply("⚠️ Format salah!\nContoh:\n`gal jasebtime1 1m 1d\nPesan yang ingin disebarkan`")
            return

        group_number, interval_str, duration_str = match.groups()
        user_id = event.sender_id

        def parse_extended_duration(dur_str):
            if dur_str == "1week":
                return 7 * 86400
            elif dur_str == "1month":
                return 30 * 86400
            return parse_interval(dur_str)

        interval = parse_interval(interval_str)
        duration = parse_extended_duration(duration_str)

        if not interval or not duration:
            await event.reply("⚠️ Format waktu/durasi salah!")
            return

        tag = f"jasebtime{group_number}"

        if user_id not in active_bc_interval:
            active_bc_interval[user_id] = {}

        if active_bc_interval[user_id].get(tag):
            await event.reply(f"⚠️ Broadcast jasebtime{group_number} sudah aktif.")
            return

        # Menyimpan status aktif untuk menunggu pesan
        active_bc_interval[user_id][tag] = {'status': 'waiting_for_message', 'interval': interval, 'duration': duration}
        await event.reply(f"✅ Memulai `gal jasebtime{group_number}` tiap `{interval_str}` selama `{duration_str}`.\nSilakan kirimkan pesan yang ingin disebarkan.")

    # Menangani pesan yang dikirimkan oleh user untuk disebarkan
    @client.on(events.NewMessage)
    async def handle_broadcast_message(event):
        user_id = event.sender_id
        for tag, data in active_bc_interval.get(user_id, {}).items():
            if data['status'] == 'waiting_for_message':
                message = event.raw_text  # Pesan yang akan disebarkan
                interval = data['interval']
                duration = data['duration']

                # Perbarui status menjadi broadcasting
                active_bc_interval[user_id][tag]['status'] = 'broadcasting'
                await event.reply(f"✅ Pesan diterima. Memulai penyebaran pesan setiap `{interval}` selama `{duration}`.")

                # Fungsi untuk mulai menyebarkan pesan
                async def timed_jaseb_broadcast():
                    end_time = asyncio.get_event_loop().time() + duration
                    while active_bc_interval[user_id].get(tag) and asyncio.get_event_loop().time() < end_time:
                        async for dialog in client.iter_dialogs():
                            if dialog.is_group and dialog.id not in blacklist:
                                try:
                                    # Mengirim pesan ke grup
                                    await client.send_message(dialog.id, message)
                                except Exception as e:
                                    print(f"Error saat mengirim pesan: {e}")
                        await asyncio.sleep(interval)

                    # Setelah selesai, set status menjadi finished
                    active_bc_interval[user_id][tag]['status'] = 'finished'
                    await event.reply(f"⏰ Penyebaran pesan selesai setelah `{duration}`.")

                # Menjalankan penyebaran pesan
                asyncio.create_task(timed_jaseb_broadcast())
                
                break




    @client.on(events.NewMessage(pattern=r'^gal stopjasebtime(\d+)$'))
    async def stop_jasebtime_group_handler(event):
        group_number = event.pattern_match.group(1)
        user_id = event.sender_id
        tag = f"jasebtime{group_number}"

        if active_bc_interval[user_id].get(tag):
            active_bc_interval[user_id][tag] = False
            await event.reply(f"✅ jasebtime{group_number} dihentikan secara manual.")
        else:
            await event.reply(f"⚠️ Tidak ada jasebtime{group_number} yang aktif.")


    # Hentikan broadcast grup
    @client.on(events.NewMessage(pattern=r'^gal stopbcstargr(\d+)$'))
    async def stop_broadcast_group_handler(event):
        group_number = event.pattern_match.group(1)
        if active_bc_interval[user_id][f"group{group_number}"]:
            active_bc_interval[user_id][f"group{group_number}"] = False
            await event.reply(f"✅ Broadcast ke grup {group_number} dihentikan.")
        else:
            await event.reply(f"⚠️ Tidak ada broadcast grup {group_number} yang berjalan.")

    # Tambahkan grup/chat ke blacklist
    @client.on(events.NewMessage(pattern=r'^gal bl$'))
    async def blacklist_handler(event):
        chat_id = event.chat_id
        blacklist.add(chat_id)
        await event.reply("✅ Grup ini telah ditambahkan ke blacklist.")

    # Hapus grup/chat dari blacklist
    @client.on(events.NewMessage(pattern=r'^gal unbl$'))
    async def unblacklist_handler(event):
        chat_id = event.chat_id
        if chat_id in blacklist:
            blacklist.remove(chat_id)
            await event.reply("✅ Grup ini telah dihapus dari blacklist.")
        else:
            await event.reply("⚠️ Grup ini tidak ada dalam blacklist.")

        # Tampilkan daftar perintah
    @client.on(events.NewMessage(pattern=r'^gal help$'))
    async def help_handler(event):
        help_text = (
            "📋 **Daftar Perintah yang Tersedia:**\n\n"
            "1. gal hastle [pesan] [waktu][s/m/h/d]\n"
            "   Spam pesan di grup dengan interval tertentu.\n"
            "2. gal stop\n"
            "   Hentikan spam di grup.\n"
            "3. gal ping\n"
            "   Tes koneksi bot.\n"
            "4. gal bcstar [pesan]\n"
            "   Broadcast ke semua chat kecuali blacklist.\n"
            "5. gal bcstargr [waktu][s/m/h/d] [pesan]\n"
            "   Broadcast hanya ke grup dengan interval tertentu.\n"
            "6. gal stopbcstargr[1-10]\n"
            "   Hentikan broadcast ke grup tertentu.\n"
            "7. gal bl\n"
            "    Tambahkan grup/chat ke blacklist.\n"
            "8. gal unbl\n"
            "    Hapus grup/chat dari blacklist.\n"
            "9. gal jasebtime[1-10] [interval] [durasi]\n"
            "   Broadcast pesan tiap interval ke grup selama durasi tertentu.\n"
            "10. gal stopjasebtime[1-10]\n"
            "   Hentikan jasebtime tertentu.\n"
            "11. gal bcstarforwad[1-9]+ [interval] [durasi]\n"
            "   Forward pesan ke semua grup dengan interval dan durasi tertentu.\n"
            "12. gal stopbcstarforwad[1-9]+\n"
            "   Hentikan forward pesan tertentu berdasarkan tag.\n"
        )
        await event.reply(help_text)

    @client.on(events.NewMessage(pattern=r'^gal bcstargr(\d+) (\d+[smhd])'))
    async def broadcast_group_handler(event):
        lines = event.raw_text.split('\n', 1)
        match = re.match(r'^gal bcstargr(\d+) (\d+[smhd])', lines[0])
        if not match or len(lines) < 2:
            await event.reply("⚠️ Format salah!\nContoh:\n`gal bcstargr1 10s`\n`Isi pesan di sini.`")
            return

        group_number, interval_str = match.groups()
        custom_message = lines[1]
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

    from collections import defaultdict
    import asyncio
    import re

    # Menyimpan state pesan yang akan diforward
    forward_messages = defaultdict(lambda: defaultdict(lambda: None))  # {user_id: {tag: message}}

    # Counter untuk tag forward
    forward_counter = defaultdict(lambda: 1)  # {user_id: next_tag_number}

    @client.on(events.NewMessage(pattern=r'^gal bcstarforwad(\d+) (\d+[smhd]) (\d+[smhd]|1week|1month)$'))
    async def bcstarforwad_handler(event):
        lines = event.raw_text.split('\n', 1)
        match = re.match(r'^gal bcstarforwad(\d+) (\d+[smhd]) (\d+[smhd]|1week|1month)', lines[0])

        if not match or len(lines) < 2:
            await event.reply("⚠️ Format salah!\nContoh:\n`gal bcstarforwad1 1m 1d\nPesan yang ingin disebarkan`")
            return

        group_number, interval_str, duration_str = match.groups()
        user_id = event.sender_id

        def parse_extended_duration(dur_str):
            if dur_str == "1week":
                return 7 * 86400
            elif dur_str == "1month":
                return 30 * 86400
            return parse_interval(dur_str)

        interval = parse_interval(interval_str)
        duration = parse_extended_duration(duration_str)

        if not interval or not duration:
            await event.reply("⚠️ Format waktu/durasi salah!")
            return

        tag = f"bcstarforwad{group_number}"

        if user_id not in active_bc_interval:
            active_bc_interval[user_id] = {}

        if active_bc_interval[user_id].get(tag):
            await event.reply(f"⚠️ Broadcast bcstarforwad{group_number} sudah aktif.")
            return

        # Menyimpan status aktif untuk menunggu pesan yang akan diteruskan
        active_bc_interval[user_id][tag] = {'status': 'waiting_for_message', 'interval': interval, 'duration': duration}
        await event.reply(f"✅ Memulai `gal bcstarforwad{group_number}` tiap `{interval_str}` selama `{duration_str}`.\nSilakan forward pesan yang ingin disebarkan.")

    # Menangani pesan yang di-forward
    @client.on(events.NewMessage)
    async def forward_message_handler(event):
        user_id = event.sender_id
        for tag, data in active_bc_interval.get(user_id, {}).items():
            if data['status'] == 'waiting_for_message':
                # Pastikan pesan yang diterima adalah pesan yang di-forward
                if event.is_forward:
                    message = event.message.text
                    interval = data['interval']
                    duration = data['duration']
                    
                    # Perbarui status menjadi broadcasting
                    active_bc_interval[user_id][tag]['status'] = 'broadcasting'
                    await event.reply(f"✅ Pesan diterima. Memulai penyebaran pesan setiap `{interval}` selama `{duration}`.")

                    # Menjalankan proses penyebaran pesan
                    async def timed_bcstarforwad_broadcast():
                        end_time = asyncio.get_event_loop().time() + duration
                        while active_bc_interval[user_id].get(tag) and asyncio.get_event_loop().time() < end_time:
                            async for dialog in client.iter_dialogs():
                                if dialog.is_group and dialog.id not in blacklist:
                                    try:
                                        # Mengirim pesan forward ke setiap grup
                                        await client.send_message(dialog.id, message)
                                    except Exception as e:
                                        print(f"Error saat mengirim pesan: {e}")
                            await asyncio.sleep(interval)

                        # Setelah selesai, matikan status broadcast
                        active_bc_interval[user_id][tag]['status'] = 'finished'
                        await event.reply(f"⏰ Penyebaran pesan selesai setelah `{duration}`.")

                    asyncio.create_task(timed_bcstarforwad_broadcast())
                
                break


    # Hentikan penyebaran pesan forward tertentu secara manual
    @client.on(events.NewMessage(pattern=r'^gal stopbcstarforwad(\d+)$'))
    async def stop_forward_broadcast(event):
        tag_number = event.pattern_match.group(1)
        user_id = event.sender_id
        tag = f"forwad{tag_number}"

        if active_bc_interval[user_id].get(tag):
            active_bc_interval[user_id][tag] = False
            forward_messages[user_id][tag] = None
            await event.reply(f"✅ Penyebaran pesan forward {tag} dihentikan.")
        else:
            await event.reply(f"⚠️ Tidak ada penyebaran forward {tag} yang berjalan.")




    # Menangani auto-reply
    @client.on(events.NewMessage(incoming=True))
    async def auto_reply_handler(event):
        if event.is_private and user_id in auto_replies and auto_replies[user_id]:
            try:
                sender = await event.get_sender()
                peer = InputPeerUser(sender.id, sender.access_hash)
                await client.send_message(peer, auto_replies[user_id])
                await client.send_read_acknowledge(peer)
            except errors.rpcerrorlist.UsernameNotOccupiedError:
                pass  # Jangan tampilkan error
            except errors.rpcerrorlist.FloodWaitError as e:
                pass  # Jangan tampilkan error
            except Exception as e:
                pass  # Jangan tampilkan error

    # Hentikan semua pengaturan
    @client.on(events.NewMessage(pattern=r'^gal stopall$'))
    async def stop_all_handler(event):
        for group_key in active_bc_interval[user_id].keys():
            active_bc_interval[user_id][group_key] = False
        auto_replies[user_id] = ""
        blacklist.clear()
        for group_id in active_groups.keys():
            active_groups[group_id][user_id] = False
        for group_key in active_bc_interval[user_id].keys():
            if active_bc_interval[user_id][group_key]:
                active_bc_interval[user_id][group_key] = False
        await event.reply("\u2705 Semua pengaturan telah direset dan semua broadcast dihentikan.")
