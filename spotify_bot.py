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
        "Saya adalah bot musik multifungsi. Kirimkan saya judul lagu atau nama artis untuk memulai pencarian.\n\n"
        "Gunakan perintah /cari [judul lagu], /album, atau /artist untuk fitur lainnya.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan bantuan saat pengguna mengirim /help."""
    await update.message.reply_text(
        "Berikut cara menggunakan saya:\n\n"
        "*FITUR LAGU:*\n"
        "🎵 /cari [judul lagu/artis] - Untuk mencari lagu spesifik.\n"
        "✍️ Kamu juga bisa langsung mengetikkan judul lagu atau artis tanpa perintah apa pun!\n\n"
        "*FITUR ALBUM:*\n"
        "💿 /album - Menampilkan menu fitur album.\n"
        "🔎 /getalbum [nama album] - Mencari detail album.\n"
        "🎲 /randomalbum - Menampilkan 5 album acak.\n"
        "✨ /getnewreleases - Menampilkan 5 rilis album terbaru.\n\n"
        "*FITUR ARTIS:*\n"
        "👤 /artist - Menampilkan menu fitur artis.\n"
        "🎤 /getartist [nama artis] - Mencari detail artis.\n"
        "🎲 /randomartist - Menampilkan 5 artis acak.\n"
        "💿 /getartistalbums [nama artis] - Menampilkan album dari artis.\n"
        "🏆 /gettoptracks [nama artis] - Menampilkan lagu terpopuler dari artis.\n"
        "🤝 /getrelated [nama artis] - Menampilkan artis serupa."
    )

async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fungsi utama untuk mencari musik di Spotify."""
    if context.args:
        query = " ".join(context.args)
    elif update.message.text:
        query = update.message.text
    else:
        await update.message.reply_text("Tolong berikan judul lagu atau nama artis untuk saya cari.")
        return

    await update.message.reply_text(f"🔍 Mencari lagu '{query}' di Spotify...")

    try:
        results = sp.search(q=query, limit=5, type='track')
        tracks = results['tracks']['items']

        if not tracks:
            safe_query = escape_markdown(query, version=2)
            await update.message.reply_text(f"Maaf, saya tidak dapat menemukan lagu untuk *'{safe_query}'*\\. Coba kata kunci lain\\.", parse_mode='MarkdownV2')
            return

        for track in tracks:
            await send_track_info(update, context, track)

    except Exception as e:
        logger.error(f"Error saat mencari musik: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan Spotify. Coba lagi nanti.")

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

async def send_artist_info(update: Update, context: ContextTypes.DEFAULT_TYPE, artist: dict):
    """Fungsi pembantu untuk mengirim informasi artis yang ringkas."""
    artist_name = escape_markdown(artist['name'], version=2)
    spotify_url = artist['external_urls']['spotify']
    artist_image_url = artist['images'][0]['url'] if artist['images'] else None
    genres = escape_markdown(", ".join(artist['genres']) or "Tidak ada genre", version=2)
    popularity = artist['popularity']

    caption = (
        f"🎤 *Artis:* {artist_name}\n"
        f"🔥 *Popularitas:* {popularity}/100\n"
        f"🏷️ *Genre:* {genres}\n\n"
        f"[Buka di Spotify]({spotify_url})"
    )

    if artist_image_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=artist_image_url, caption=caption, parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(caption, parse_mode='MarkdownV2')

async def send_track_info(update: Update, context: ContextTypes.DEFAULT_TYPE, track: dict):
    """Fungsi pembantu untuk mengirim informasi lagu yang ringkas."""
    track_name = escape_markdown(track['name'], version=2)
    artists = escape_markdown(", ".join([artist['name'] for artist in track['artists']]), version=2)
    album_name = escape_markdown(track['album']['name'], version=2)
    spotify_url = track['external_urls']['spotify']
    album_cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None

    caption = (
        f"🎵 *Lagu:* {track_name}\n"
        f"👤 *Artis:* {artists}\n"
        f"💿 *Album:* {album_name}\n\n"
        f"[Buka di Spotify]({spotify_url})"
    )
    
    if album_cover_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=album_cover_url, caption=caption, parse_mode='MarkdownV2')
    else:
            await update.message.reply_text(caption, parse_mode='MarkdownV2')

# --- Fitur Album ---

async def album_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu untuk fitur-fitur terkait album."""
    await update.message.reply_text(
        "Selamat datang di Menu Album!\n\n"
        "Berikut adalah perintah yang bisa kamu gunakan:\n\n"
        "🔎 /getalbum [nama album]\nUntuk mencari detail album spesifik.\n\n"
        "🎲 /randomalbum\nUntuk menampilkan 5 album acak.\n\n"
        "✨ /getnewreleases\nUntuk menampilkan 5 album rilis terbaru.",
        parse_mode='Markdown'
    )

async def get_album_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari dan menampilkan detail dari sebuah album spesifik."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama album. Contoh: /getalbum My Beautiful Dark Twisted Fantasy")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Mencari album '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='album')
        album_results = results['albums']['items']

        if not album_results:
            safe_query = escape_markdown(query, version=2)
            await update.message.reply_text(f"Maaf, album *'{safe_query}'* tidak ditemukan\\.", parse_mode='MarkdownV2')
            return

        album_id = album_results[0]['id']
        album = sp.album(album_id)

        album_name = escape_markdown(album['name'], version=2)
        artists = escape_markdown(", ".join([artist['name'] for artist in album['artists']]), version=2)
        release_date = escape_markdown(album['release_date'], version=2)
        total_tracks = album['total_tracks']
        spotify_url = album['external_urls']['spotify']
        genres = escape_markdown(", ".join(album['genres']) or "Tidak ada genre", version=2)
        album_cover_url = album['images'][0]['url'] if album['images'] else None

        caption = (
            f"💿 *Album:* {album_name}\n"
            f"👤 *Artis:* {artists}\n"
            f"🗓️ *Tanggal Rilis:* {release_date}\n"
            f"🎶 *Total Lagu:* {total_tracks}\n"
            f"🏷️ *Genre:* {genres}\n\n"
            f"[Buka di Spotify]({spotify_url})"
        )

        if album_cover_url:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=album_cover_url, caption=caption, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(caption, parse_mode='MarkdownV2')

    except Exception as e:
        logger.error(f"Error saat mengambil detail album: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil detail album.")

async def get_random_albums(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan menampilkan 5 album secara acak."""
    await update.message.reply_text("🎲 Mengambil 5 album acak...")
    try:
        random_char = random.choice("abcdefghijklmnopqrstuvwxyz")
        random_offset = random.randint(0, 500)
        results = sp.search(q=f'year:2000-2025 track:{random_char}', type='album', limit=5, offset=random_offset)
        
        albums = results['albums']['items']
        if not albums:
            await update.message.reply_text("Gagal mendapatkan album acak, coba lagi!")
            return

        for album in albums:
            await send_album_info(update, context, album)

    except Exception as e:
        logger.error(f"Error saat mengambil album acak: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil album acak.")

async def get_new_releases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan menampilkan 5 album rilis terbaru."""
    await update.message.reply_text("✨ Menampilkan 5 rilis album terbaru...")
    try:
        results = sp.new_releases(limit=5)
        albums = results['albums']['items']

        for album in albums:
            await send_album_info(update, context, album)

    except Exception as e:
        logger.error(f"Error saat mengambil rilis terbaru: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil rilis terbaru.")

# --- Fitur Artis ---

async def artist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu untuk fitur-fitur terkait artis."""
    await update.message.reply_text(
        "Selamat datang di Menu Artis!\n\n"
        "Berikut adalah perintah yang bisa kamu gunakan:\n\n"
        "🎤 /getartist [nama artis] - Mencari detail artis.\n"
        "🎲 /randomartist - Menampilkan 5 artis acak.\n"
        "💿 /getartistalbums [nama artis] - Menampilkan album dari artis.\n"
        "🏆 /gettoptracks [nama artis] - Menampilkan lagu terpopuler dari artis.\n"
        "🤝 /getrelated [nama artis] - Menampilkan artis serupa.",
        parse_mode='Markdown'
    )

async def get_artist_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari dan menampilkan detail dari seorang artis."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama artis. Contoh: /getartist Tulus")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Mencari artis '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='artist')
        artist_results = results['artists']['items']

        if not artist_results:
            safe_query = escape_markdown(query, version=2)
            await update.message.reply_text(f"Maaf, artis *'{safe_query}'* tidak ditemukan\\.", parse_mode='MarkdownV2')
            return

        await send_artist_info(update, context, artist_results[0])

    except Exception as e:
        logger.error(f"Error saat mengambil detail artis: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil detail artis.")

async def get_random_artists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan menampilkan 5 artis secara acak."""
    await update.message.reply_text("🎲 Mengambil 5 artis acak...")
    try:
        random_char = random.choice("abcdefghijklmnopqrstuvwxyz")
        random_offset = random.randint(0, 500)
        results = sp.search(q=f'artist:{random_char}', type='artist', limit=5, offset=random_offset)
        
        artists = results['artists']['items']
        if not artists:
            await update.message.reply_text("Gagal mendapatkan artis acak, coba lagi!")
            return

        for artist in artists:
            await send_artist_info(update, context, artist)

    except Exception as e:
        logger.error(f"Error saat mengambil artis acak: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil artis acak.")

async def get_artist_albums(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil album dari artis yang dicari."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama artis. Contoh: /getartistalbums Coldplay")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"💿 Mencari album dari '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='artist')
        artist_results = results['artists']['items']

        if not artist_results:
            safe_query = escape_markdown(query, version=2)
            await update.message.reply_text(f"Maaf, artis *'{safe_query}'* tidak ditemukan\\.", parse_mode='MarkdownV2')
            return
        
        artist_id = artist_results[0]['id']
        albums = sp.artist_albums(artist_id, album_type='album', limit=10)

        if not albums['items']:
            await update.message.reply_text(f"Artis *'{escape_markdown(query, version=2)}'* tidak memiliki album\\.", parse_mode='MarkdownV2')
            return

        for album in albums['items']:
            await send_album_info(update, context, album)

    except Exception as e:
        logger.error(f"Error saat mengambil album artis: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil album artis.")

async def get_artist_top_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil lagu terpopuler dari artis yang dicari."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama artis. Contoh: /gettoptracks Queen")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🏆 Mencari lagu terpopuler dari '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='artist')
        artist_results = results['artists']['items']

        if not artist_results:
            safe_query = escape_markdown(query, version=2)
            await update.message.reply_text(f"Maaf, artis *'{safe_query}'* tidak ditemukan\\.", parse_mode='MarkdownV2')
            return
        
        artist_id = artist_results[0]['id']
        # Menggunakan 'ID' untuk pasar Indonesia
        top_tracks = sp.artist_top_tracks(artist_id, country='ID')

        if not top_tracks['tracks']:
            await update.message.reply_text(f"Tidak dapat menemukan lagu terpopuler untuk *'{escape_markdown(query, version=2)}'*\\.", parse_mode='MarkdownV2')
            return

        for track in top_tracks['tracks']:
            await send_track_info(update, context, track)

    except Exception as e:
        logger.error(f"Error saat mengambil lagu terpopuler: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil lagu terpopuler.")

async def get_related_artists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil artis yang serupa/terkait."""
    if not context.args:
        await update.message.reply_text("Tolong berikan nama artis. Contoh: /getrelated Daft Punk")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🤝 Mencari artis yang terkait dengan '{query}'...")

    try:
        results = sp.search(q=query, limit=1, type='artist')
        artist_results = results['artists']['items']

        if not artist_results:
            safe_query = escape_markdown(query, version=2)
            await update.message.reply_text(f"Maaf, artis *'{safe_query}'* tidak ditemukan\\.", parse_mode='MarkdownV2')
            return
        
        artist_id = artist_results[0]['id']
        related_artists = sp.artist_related_artists(artist_id)

        if not related_artists['artists']:
            await update.message.reply_text(f"Tidak dapat menemukan artis terkait untuk *'{escape_markdown(query, version=2)}'*\\.", parse_mode='MarkdownV2')
            return

        await update.message.reply_text(f"Berikut 5 artis yang mirip dengan *{escape_markdown(query, version=2)}*:", parse_mode='MarkdownV2')
        for artist in related_artists['artists'][:5]:
            await send_artist_info(update, context, artist)

    except Exception as e:
        logger.error(f"Error saat mengambil artis terkait: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil artis terkait.")

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
    application.add_handler(CommandHandler("cari", search_music))

    # Handler untuk fitur album
    application.add_handler(CommandHandler("album", album_menu))
    application.add_handler(CommandHandler("getalbum", get_album_details))
    application.add_handler(CommandHandler("randomalbum", get_random_albums))
    application.add_handler(CommandHandler("getnewreleases", get_new_releases))

    # Handler untuk fitur artis
    application.add_handler(CommandHandler("artist", artist_menu))
    application.add_handler(CommandHandler("getartist", get_artist_details))
    application.add_handler(CommandHandler("randomartist", get_random_artists))
    application.add_handler(CommandHandler("getartistalbums", get_artist_albums))
    application.add_handler(CommandHandler("gettoptracks", get_artist_top_tracks))
    application.add_handler(CommandHandler("getrelated", get_related_artists))

    # Message Handler untuk pencarian langsung (harus setelah command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))
    
    # Handler untuk perintah yang tidak dikenali (harus diletakkan paling akhir)
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot Telegram siap dijalankan...")
    application.run_polling()

if __name__ == "__main__":
    main()
