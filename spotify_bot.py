import os
import logging
import random
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import escape_markdown

# --- Memuat Environment Variables dari file .env ---
# Langkah ini penting agar kunci API Anda aman dan tidak tertulis langsung di kode.
load_dotenv()

# --- Konfigurasi Awal ---
# Mengaktifkan logging untuk membantu debug jika terjadi error
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Mengatur level log untuk httpx agar tidak terlalu "berisik" di konsol
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Otentikasi Spotify ---
# Mengambil kredensial dari environment variables yang sudah dimuat oleh load_dotenv()
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

# Mengecek apakah kredensial Spotify sudah diatur
if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET]):
    raise ValueError("Pastikan SPOTIPY_CLIENT_ID dan SPOTIPY_CLIENT_SECRET sudah diatur di file .env Anda.")

# Menginisialisasi klien Spotipy dengan mode "Client Credentials"
# Mode ini cocok untuk mengakses data publik Spotify tanpa login pengguna
try:
    auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    logger.info("Otentikasi dengan Spotify berhasil!")
except Exception as e:
    logger.error(f"Gagal otentikasi dengan Spotify: {e}")
    exit()

# --- Fungsi-fungsi untuk Command Handler Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan saat pengguna memulai bot dengan /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo, {user.mention_html()}!\n\n"
        "Saya adalah bot musik multifungsi. Gunakan perintah /cari, /album, atau /artist untuk menjelajahi fitur-fitur yang ada.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan bantuan saat pengguna mengirim /help."""
    await update.message.reply_text(
        "Berikut cara menggunakan saya:\n\n"
        "*FITUR PENCARIAN:*\n"
        "🔎 /cari - Menampilkan menu pencarian.\n"
        "🎵 /caritrack [nama lagu] - Mencari lagu beserta detail albumnya.\n"
        "🎤 /cariartist [nama artis] - Mencari artis dan statistiknya.\n"
        "💿 /carialbum [nama album] - Mencari album dan detailnya.\n\n"
        "*FITUR ALBUM:*\n"
        "💿 /album - Menampilkan menu fitur album.\n"
        "🎲 /randomalbum - Menampilkan 5 album acak.\n"
        "✨ /getnewreleases - Menampilkan 5 rilis album terbaru.\n\n"
        "*FITUR ARTIS:*\n"
        "👤 /artist - Menampilkan menu fitur artis.\n"
        "🎲 /randomartist - Menampilkan 5 artis acak.\n"
        "💿 /getartistalbums [nama artis] - Menampilkan album dari artis.\n"
        "🏆 /gettoptracks [nama artis] - Menampilkan lagu terpopuler dari artis.\n"
        "� /getrelated [nama artis] - Menampilkan artis serupa."
    )

# --- Fungsi Pembantu (Helpers) ---

async def send_album_info(update: Update, context: ContextTypes.DEFAULT_TYPE, album: dict):
    """Fungsi pembantu untuk mengirim informasi album yang ringkas."""
    album_name = escape_markdown(album['name'], version=2)
    artists = escape_markdown(", ".join([artist['name'] for artist in album['artists']]), version=2)
    spotify_url = album['external_urls']['spotify']
    album_cover_url = album['images'][0]['url'] if album['images'] else None
    release_date = escape_markdown(album['release_date'], version=2)

    caption = (
        f"💿 *Album:* {album_name}\n"
        f"👤 *Artis:* {artists}\n"
        f"🗓️ *Rilis:* {release_date}\n\n"
        f"[Buka di Spotify]({spotify_url})"
    )

    if album_cover_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=album_cover_url, caption=caption, parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(caption, parse_mode='MarkdownV2')

async def send_artist_info_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE, artist: dict):
    """Fungsi pembantu untuk mengirim informasi artis yang detail."""
    artist_name = escape_markdown(artist['name'], version=2)
    spotify_url = artist['external_urls']['spotify']
    artist_image_url = artist['images'][0]['url'] if artist['images'] else None
    genres = escape_markdown(", ".join(artist['genres']) or "Tidak ada genre", version=2)
    popularity = artist['popularity']
    followers = artist['followers']['total']

    caption = (
        f"🎤 *Artis:* {artist_name}\n"
        f"🔥 *Popularitas:* {popularity}/100\n"
        f"👥 *Pengikut:* {followers:,}\n"
        f"🏷️ *Genre:* {genres}\n\n"
        f"[Buka di Spotify]({spotify_url})"
    )

    if artist_image_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=artist_image_url, caption=caption, parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(caption, parse_mode='MarkdownV2')

async def send_album_info_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE, album: dict):
    """Fungsi pembantu untuk mengirim informasi album yang detail."""
    album_name = escape_markdown(album['name'], version=2)
    artists = escape_markdown(", ".join([artist['name'] for artist in album['artists']]), version=2)
    spotify_url = album['external_urls']['spotify']
    album_cover_url = album['images'][0]['url'] if album['images'] else None
    release_date = escape_markdown(album['release_date'], version=2)
    total_tracks = album['total_tracks']
    album_type = escape_markdown(album['album_type'], version=2)

    caption = (
        f"💿 *Album:* {album_name}\n"
        f"👤 *Artis:* {artists}\n"
        f"🏷️ *Tipe:* {album_type}\n"
        f"🎶 *Total Lagu:* {total_tracks}\n"
        f"🗓️ *Tanggal Rilis:* {release_date}\n\n"
        f"[Buka di Spotify]({spotify_url})"
    )

    if album_cover_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=album_cover_url, caption=caption, parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(caption, parse_mode='MarkdownV2')

# --- Fitur Pencarian Baru ---
async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu untuk fitur-fitur pencarian."""
    await update.message.reply_text(
        "Selamat datang di Menu Pencarian!\n\n"
        "Gunakan perintah berikut untuk mencari berdasarkan kategori:\n\n"
        "🎵 /caritrack [nama lagu]\n"
        "🎤 /cariartist [nama artis]\n"
        "💿 /carialbum [nama album]",
        parse_mode='Markdown'
    )

async def search_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari lagu dan menampilkan detailnya beserta info album."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama lagu. Contoh: /caritrack Bohemian Rhapsody")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Mencari lagu '{query}'...")

    try:
        results = sp.search(q=query, limit=3, type='track') # Batasi 3 agar tidak spam
        tracks = results['tracks']['items']
        if not tracks:
            await update.message.reply_text(f"Maaf, lagu '{escape_markdown(query, version=2)}' tidak ditemukan\\.", parse_mode='MarkdownV2')
            return

        for track in tracks:
            track_name = escape_markdown(track['name'], version=2)
            track_url = track['external_urls']['spotify']
            track_artists = escape_markdown(", ".join([a['name'] for a in track['artists']]), version=2)
            
            # Info Album
            album_obj = track['album']
            album_name = escape_markdown(album_obj['name'], version=2)
            album_url = album_obj['external_urls']['spotify']
            album_release = escape_markdown(album_obj['release_date'], version=2)
            album_total_tracks = album_obj['total_tracks']
            album_cover_url = album_obj['images'][0]['url'] if album_obj['images'] else None

            caption = (
                f"🎵 *Lagu Ditemukan:* [{track_name}]({track_url})\n"
                f"👤 *Oleh:* {track_artists}\n\n"
                f"*\\-\\-\\- Detail Album \\-\\-\\-*\n"
                f"💿 *Album:* [{album_name}]({album_url})\n"
                f"🔢 *Total Lagu:* {album_total_tracks}\n"
                f"🗓️ *Rilis:* {album_release}"
            )

            if album_cover_url:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=album_cover_url, caption=caption, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text(caption, parse_mode='MarkdownV2')

    except Exception as e:
        logger.error(f"Error saat mencari lagu: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencari lagu.")

async def search_artists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari artis dan menampilkan detailnya."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama artis. Contoh: /cariartist Queen")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Mencari artis '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='artist')
        artists = results['artists']['items']
        if not artists:
            await update.message.reply_text(f"Maaf, artis '{escape_markdown(query, version=2)}' tidak ditemukan\\.", parse_mode='MarkdownV2')
            return
        
        await send_artist_info_detailed(update, context, artists[0])

    except Exception as e:
        logger.error(f"Error saat mencari artis: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencari artis.")

async def search_albums(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari album dan menampilkan detailnya."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama album. Contoh: /carialbum A Night at the Opera")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Mencari album '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='album')
        albums = results['albums']['items']
        if not albums:
            await update.message.reply_text(f"Maaf, album '{escape_markdown(query, version=2)}' tidak ditemukan\\.", parse_mode='MarkdownV2')
            return
        
        # Ambil detail lengkap untuk mendapatkan 'album_type'
        album_full_details = sp.album(albums[0]['id'])
        await send_album_info_detailed(update, context, album_full_details)

    except Exception as e:
        logger.error(f"Error saat mencari album: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencari album.")

# --- Fitur Album (Discovery) ---
async def album_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Selamat datang di Menu Album Discovery!\n\n🎲 /randomalbum\n✨ /getnewreleases", parse_mode='Markdown')
async def get_random_albums(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🎲 Mengambil 5 album acak...");
    try:
        results = sp.search(q=f'year:2000-2025 track:{random.choice("abcdefghijklmnopqrstuvwxyz")}', type='album', limit=5, offset=random.randint(0, 500))
        if not results['albums']['items']: await update.message.reply_text("Gagal mendapatkan album acak, coba lagi!"); return
        for album in results['albums']['items']: await send_album_info(update, context, album)
    except Exception as e: logger.error(f"Error saat mengambil album acak: {e}"); await update.message.reply_text("Maaf, terjadi kesalahan.")
async def get_new_releases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✨ Menampilkan 5 rilis album terbaru...");
    try:
        results = sp.new_releases(limit=5)
        for album in results['albums']['items']: await send_album_info(update, context, album)
    except Exception as e: logger.error(f"Error saat mengambil rilis terbaru: {e}"); await update.message.reply_text("Maaf, terjadi kesalahan.")

# --- Fitur Artis (Discovery) ---
async def artist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Selamat datang di Menu Artis Discovery!\n\n🎲 /randomartist\n💿 /getartistalbums [nama artis]\n🏆 /gettoptracks [nama artis]\n🤝 /getrelated [nama artis]", parse_mode='Markdown')
async def get_random_artists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🎲 Mengambil 5 artis acak...");
    try:
        random_char = random.choice("abcdefghijklmnopqrstuvwxyz"); query = f'{random_char}%'; random_offset = random.randint(0, 900)
        results = sp.search(q=query, type='artist', limit=5, offset=random_offset)
        if not results['artists']['items']: await update.message.reply_text("Gagal mendapatkan artis acak, coba lagi!"); return
        for artist in results['artists']['items']: await send_artist_info_detailed(update, context, artist)
    except Exception as e: logger.error(f"Error saat mengambil artis acak: {e}"); await update.message.reply_text("Maaf, terjadi kesalahan.")
async def get_artist_albums(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Contoh: /getartistalbums Coldplay"); return
    query = " ".join(context.args); await update.message.reply_text(f"💿 Mencari album dari '{query}'...")
    try:
        results = sp.search(q=query, limit=1, type='artist')
        if not results['artists']['items']: await update.message.reply_text(f"Maaf, artis *'{escape_markdown(query, version=2)}'* tidak ditemukan\\.", parse_mode='MarkdownV2'); return
        artist_id = results['artists']['items'][0]['id']; albums = sp.artist_albums(artist_id, album_type='album', limit=10)
        if not albums['items']: await update.message.reply_text(f"Artis *'{escape_markdown(query, version=2)}'* tidak memiliki album\\.", parse_mode='MarkdownV2'); return
        for album in albums['items']: await send_album_info(update, context, album)
    except Exception as e: logger.error(f"Error saat mengambil album artis: {e}"); await update.message.reply_text("Maaf, terjadi kesalahan.")
async def get_artist_top_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Contoh: /gettoptracks Queen"); return
    query = " ".join(context.args); await update.message.reply_text(f"🏆 Mencari lagu terpopuler dari '{query}'...")
    try:
        results = sp.search(q=query, limit=1, type='artist')
        if not results['artists']['items']: await update.message.reply_text(f"Maaf, artis *'{escape_markdown(query, version=2)}'* tidak ditemukan\\.", parse_mode='MarkdownV2'); return
        artist_id = results['artists']['items'][0]['id']; top_tracks = sp.artist_top_tracks(artist_id, country='ID')
        if not top_tracks['tracks']: await update.message.reply_text(f"Tidak dapat menemukan lagu terpopuler untuk *'{escape_markdown(query, version=2)}'*\\.", parse_mode='MarkdownV2'); return
        for track in top_tracks['tracks']: await send_track_info(update, context, track)
    except Exception as e: logger.error(f"Error saat mengambil lagu terpopuler: {e}"); await update.message.reply_text("Maaf, terjadi kesalahan.")
async def get_related_artists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Contoh: /getrelated Daft Punk"); return
    query = " ".join(context.args); await update.message.reply_text(f"🤝 Mencari artis yang terkait dengan '{query}'...")
    try:
        results = sp.search(q=query, limit=1, type='artist')
        if not results['artists']['items']: await update.message.reply_text(f"Maaf, artis *'{escape_markdown(query, version=2)}'* tidak ditemukan\\.", parse_mode='MarkdownV2'); return
        artist_id = results['artists']['items'][0]['id']; related_artists = sp.artist_related_artists(artist_id)
        if not related_artists['artists']: await update.message.reply_text(f"Tidak dapat menemukan artis terkait untuk *'{escape_markdown(query, version=2)}'*\\.", parse_mode='MarkdownV2'); return
        await update.message.reply_text(f"Berikut 5 artis yang mirip dengan *{escape_markdown(query, version=2)}*:", parse_mode='MarkdownV2')
        for artist in related_artists['artists'][:5]: await send_artist_info_detailed(update, context, artist)
    except Exception as e: logger.error(f"Error saat mengambil artis terkait: {e}"); await update.message.reply_text("Maaf, terjadi kesalahan.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah yang tidak dikenali oleh bot."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Maaf, saya tidak mengerti perintah itu. Coba /help.")

def main() -> None:
    """Fungsi utama untuk menginisialisasi dan menjalankan bot."""
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        raise ValueError("Pastikan TELEGRAM_TOKEN sudah diatur di file .env Anda.")

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # --- Mendaftarkan semua Handler ke aplikasi ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Handler untuk fitur pencarian baru
    application.add_handler(CommandHandler("cari", search_menu))
    application.add_handler(CommandHandler("caritrack", search_tracks))
    application.add_handler(CommandHandler("cariartist", search_artists))
    application.add_handler(CommandHandler("carialbum", search_albums))

    # Handler untuk fitur album discovery
    application.add_handler(CommandHandler("album", album_menu))
    application.add_handler(CommandHandler("randomalbum", get_random_albums))
    application.add_handler(CommandHandler("getnewreleases", get_new_releases))

    # Handler untuk fitur artis discovery
    application.add_handler(CommandHandler("artist", artist_menu))
    application.add_handler(CommandHandler("randomartist", get_random_artists))
    application.add_handler(CommandHandler("getartistalbums", get_artist_albums))
    application.add_handler(CommandHandler("gettoptracks", get_artist_top_tracks))
    application.add_handler(CommandHandler("getrelated", get_related_artists))
    
    # Handler untuk perintah yang tidak dikenali (harus diletakkan paling akhir)
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot Telegram siap dijalankan...")
    application.run_polling()

if __name__ == "__main__":
    main()
