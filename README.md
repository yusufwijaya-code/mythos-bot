# Bot Trading Mythos

Sistem trading crypto otomatis dengan risk management, backtesting, notifikasi WhatsApp, dan dashboard web.

---

## Fitur Utama

- Trading otomatis (BUY/SELL) menggunakan Binance API
- Paper Trading Mode (default) & Live Trading Mode
- Strategi: EMA Crossover + RSI + MACD + Volume confirmation
- Multi-timeframe strategy
- Risk management: Stop Loss, Take Profit, Trailing Stop, Max Daily Loss
- Backtesting dengan metrik lengkap (win rate, profit factor, max drawdown, Sharpe ratio)
- Notifikasi WhatsApp via Fonnte
- Dashboard web real-time
- Email/Password login dengan bcrypt hashing
- JWT token-based authentication untuk semua API
- Bot Health Monitoring (engine status, API connectivity, CPU/memory, error rate)
- Health Alert otomatis via WhatsApp jika sistem bermasalah
- Failsafe system (auto-stop jika error terlalu banyak atau balance turun drastis)

---

## Struktur Project

```
bot-trading-mythos/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── core/                 # Database, trading engine, risk manager
│   ├── api/endpoints/        # API routes (dashboard, control, backtest)
│   ├── indicators/           # EMA, RSI, MACD, Volume, Support/Resistance
│   ├── strategies/           # EMA Crossover, Multi-timeframe
│   ├── models/               # SQLAlchemy ORM models
│   ├── repositories/         # Data access layer
│   ├── services/             # Binance client, paper trading
│   ├── auth/                 # Password auth (bcrypt), JWT, dependencies
│   ├── workers/              # Scheduler
│   ├── notifications/        # Fonnte (WhatsApp)
│   └── utils/                # Logger, helpers
├── backtesting/              # Backtesting engine & reports
├── config/                   # Settings & .env
├── dashboard/                # HTML/JS dashboard
├── database/                 # MySQL schema
├── docker/                   # Dockerfile & docker-compose
├── scripts/                  # Entry point scripts
├── logs/                     # Log files
├── tests/                    # Unit tests
└── requirements.txt
```

---

## Panduan Deployment Step-by-Step (Bahasa Indonesia)

### 1. Daftar & Beli Server di IDCloudHost

#### 1a. Membuat Akun

1. Buka https://idcloudhost.com
2. Klik **Register** di atas kanan
3. Isi formulir:
   - **Full Name**: Nama lengkap Anda
   - **Email**: Email aktif
   - **Password**: Minimal 8 karakter
   - **Phone**: Nomor telepon (+62...)
4. Centang "I agree to the Terms of Service"
5. Klik **Create Account** → Verifikasi email Anda

#### 1b. Top-Up Saldo

1. Login ke akun IDCloudHost
2. Di dashboard, klik **Billing** → **Top Up Balance**
3. Pilih jumlah (minimal Rp 50.000)
4. Pilih metode pembayaran:
   - **Transfer Bank** (BCA, Mandiri, BNI, etc.)
   - **GCash** (jika di Filipina)
   - **Credit Card** (Visa/Mastercard)
5. Selesaikan pembayaran → Saldo masuk ke akun

#### 1c. Membuat Server (Cloud Compute)

1. Login dan buka dashboard IDCloudHost
2. Di top menu, klik **Services** → **Order New Services**
3. Cari dan pilih **Cloud Compute** atau **Server VPS Pro**
3. Pilih konfigurasi:
   - **OS**: Ubuntu 22.04 LTS
   - **Plan**:
     - **Minimal**: 1 Core, 1GB RAM, 20GB SSD (Rp ~40.000/bulan)
     - **Recommended**: 2 Core, 2GB RAM, 40GB SSD (Rp ~70.000/bulan)
     - **Better**: 2 Core, 4GB RAM, 60GB SSD (Rp ~100.000/bulan)
   - **Location**: Jakarta (terdekat untuk kecepatan)
   - **Billing Cycle**: Monthly (Bulanan)
4. Klik **Create** atau **Deploy**
5. Tunggu 1-2 menit server siap (status **Running**)
6. **Catat informasi:**
   - **IP Address** (Public IP)
   - **Username**: root
   - **Password**: Dikirim ke email Anda

> **Tips Hemat:** Cek promo IDCloudHost di Twitter/Instagram mereka, sering ada diskon 50%+

### 2. Connect ke Server via SSH

#### 2a. Menggunakan Windows PowerShell/Terminal

```bash
ssh root@IP_SERVER_ANDA
```

Masukkan password saat diminta. Contoh:
```bash
ssh root@103.174.100.50
root@103.174.100.50's password: [paste password dari email]
```

Setelah login sukses, prompt akan berubah menjadi `root@server-name:~#`

#### 2b. Menggunakan PuTTY (Alternatif Windows)

1. Download PuTTY dari https://putty.org
2. Buka PuTTY.exe
3. **Host Name**: Paste IP Address dari IDCloudHost
4. **Port**: 22 (default)
5. **Connection type**: SSH
6. Klik **Open**
7. Username: `root`
8. Password: Paste dari email

#### 2c. Mengubah Password Root (Opsional tapi DISARANKAN)

Untuk keamanan, ubah password default:
```bash
passwd
# Masukkan password lama (dari email)
# Masukkan password baru (2x untuk konfirmasi)
```

#### 2d. Mengatur Firewall (Security)

```bash
# Install UFW (Uncomplicated Firewall)
sudo apt install -y ufw

# Izinkan SSH agar tidak terkunci
sudo ufw allow 22/tcp

# Aktifkan firewall
sudo ufw enable

# Verifikasi
sudo ufw status
```

### 3. Install Python & Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Verifikasi
python3.11 --version
python3 --version
pip --version
```

### 4. Setup Project

```bash
# Clone atau upload project
cd /home
mkdir bot-trading-mythos
cd bot-trading-mythos

# Upload semua file project ke folder ini (bisa pakai SCP atau FileZilla)
# Contoh SCP dari komputer lokal:
# scp -r C:\Apache24\htdocs\bot-ucup\bot-trading-mythos\* root@IP_SERVER:/home/bot-trading-mythos/

# Buat virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Setup Database MySQL (RECOMMENDED)

Install MySQL langsung ke server:

```bash
# Install MySQL Server
sudo apt install -y mysql-server

# (Optional) Secure installation
sudo mysql_secure_installation
```

**Setup Database & Tables:**

```bash
# Login ke MySQL (tanpa password, karena root belum ada password)
sudo mysql -u root

# Buat database dan tables dari init.sql
source /home/bot-trading-mythos/database/init.sql;

# Verifikasi
SHOW DATABASES;
USE bot_trading_;
SHOW TABLES;
exit;
```

**Verifikasi MySQL berjalan:**

```bash
sudo systemctl status mysql
sudo systemctl start mysql
```

> **Note:** Hindari Docker untuk database di VPS budget (CPU x86-64-v2 tidak support). MySQL native lebih stabil & cepat.

### 6. Setup Binance API

1. Login ke https://www.binance.com
2. Buka menu **API Management** (di profil akun)
3. Klik **Create API** → Pilih **System Generated**
4. Beri nama API, contoh: "Bot Trading "
5. **PENTING - Setting Permissions:**
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ❌ **JANGAN** enable Withdrawals (keamanan)
6. Copy **API Key** dan **Secret Key**

### 7. Setup Fonnte API (WhatsApp)

1. Buka https://fonnte.com dan daftar akun
2. Hubungkan nomor WhatsApp: **+6282114939571** (scan QR code)
3. Setelah terhubung, copy **Token** dari dashboard Fonnte
4. Token ini digunakan untuk mengirim notifikasi ke **+62895394755672**

### 8. Setup Authentication Password Hash

Login menggunakan email + password dengan bcrypt hashing.

Jalankan perintah di server untuk generate bcrypt hash:

```bash
cd /home/bot-trading-
source venv/bin/activate
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('@091375'))"
```

**Output contoh:**
```
$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Uy1yK3lVtQkqB1Zq
```

Copy hash tersebut untuk langkah 9 (`.env` configuration).

### 9. Konfigurasi Environment Variables

```bash
cd /home/bot-trading-
nano config/.env
```

Edit file `.env` dan isi dengan kredensial Anda:
```
# --- Binance API ---
BINANCE_API_KEY=paste_api_key_binance_anda
BINANCE_API_SECRET=paste_secret_key_binance_anda

# --- Database (MySQL) ---
DB_HOST=localhost
DB_PORT=3306
DB_NAME=bot_trading_
DB_USER=root
DB_PASSWORD=password_mysql_anda

# --- Fonnte (WhatsApp) ---
FONNTE_TOKEN=paste_token_fonnte_anda
FONNTE_SENDER=6282114939571
FONNTE_TARGET=62895394755672

# --- Authentication ---
AUTH_PASSWORD_HASH=paste_bcrypt_hash_dari_step_8
JWT_SECRET_KEY=ganti_dengan_string_random_yang_panjang
AUTHORIZED_EMAILS=yusufwijaya3@gmail.com

# --- Trading Settings ---
TRADING_MODE=paper
TRADING_PAIRS=BTCUSDT,ETHUSDT
TIMEFRAME=1h

# --- Risk Management ---
STOP_LOSS_PCT=2.0
TAKE_PROFIT_PCT=4.0
MAX_POSITION_PCT=10.0
MAX_DAILY_LOSS_PCT=5.0
TRAILING_STOP_PCT=1.5
MAX_TRADES_PER_DAY=10

# --- Paper Trading ---
PAPER_INITIAL_BALANCE=10000.0

# --- Server ---
API_HOST=0.0.0.0
API_PORT=8000
```

Simpan: `Ctrl+O` → Enter → `Ctrl+X`

> **Tips JWT_SECRET_KEY:** Buat secret key random dengan perintah:
> ```bash
> python3 -c "import secrets; print(secrets.token_hex(32))"
> ```

### 10. Cara Menjalankan Bot

**Opsi A: Menjalankan langsung (RECOMMENDED untuk testing):**
```bash
cd /home/bot-trading-
source venv/bin/activate
python scripts/run_bot.py
```

Setelah bot jalan, buka dashboard di browser: `http://IP_SERVER_ANDA:8000`

**Opsi B: Menjalankan sebagai background service (systemd):**
Lanjut ke Section 12 untuk setup auto-run 👇

### 11. Cara Membuka Dashboard & Login

Buka browser dan akses:
```
http://IP_SERVER_ANDA:8000
```

**Login dengan:**
- **Email:** `yusufwijaya3@gmail.com`
- **Password:** `Mythosxxxxx`

Dashboard menampilkan:
- Balance overview
- Open positions
- Trade history
- PnL chart
- System logs
- Bot control (start/stop/mode/strategy)
- Backtesting
- Health monitoring (engine status, API connectivity, CPU/memory, error rate)

### 12. Setup Auto-Run (systemd)

Agar bot berjalan otomatis saat server restart:

```bash
sudo nano /etc/systemd/system/mythos-bot.service
```

Isi file:
```ini
[Unit]
Description=Bot Trading Mythos
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/bot-trading-mythos
Environment=PATH=/home/bot-trading-mythos/venv/bin:/usr/bin
ExecStart=/home/bot-trading-mythos/venv/bin/python scripts/run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Aktifkan service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mythos-bot
sudo systemctl start mythos-bot

# Cek status
sudo systemctl status mythos-bot

# Lihat logs
journalctl -u mythos-bot -f
```

### 13. Monitoring & Troubleshooting

**Cek status bot:**
```bash
sudo systemctl status mythos-bot
```

**Lihat log real-time:**
```bash
# Via systemd
journalctl -u mythos-bot -f

# Via file log
tail -f /home/bot-trading-mythos/logs/bot_*.log
```

**Lihat log error:**
```bash
tail -f /home/bot-trading-mythos/logs/errors_*.log
```

**Restart bot:**
```bash
sudo systemctl restart mythos-bot
```

**Stop bot:**
```bash
sudo systemctl stop mythos-bot
```

**Cek penggunaan resource:**
```bash
htop
```

**Troubleshooting umum:**

| Masalah | Solusi |
|---------|--------|
| Bot tidak start | Cek `journalctl -u mythos-bot -f` untuk error |
| Database error | Pastikan MySQL berjalan: `sudo systemctl status mysql` |
| Binance error | Cek API key dan IP whitelist di Binance |
| WhatsApp tidak terkirim | Cek token Fonnte dan status koneksi di dashboard Fonnte |
| Dashboard tidak bisa diakses | Pastikan port 8000 terbuka di firewall |
| Login email/password gagal | Cek AUTH_PASSWORD_HASH di .env, pastikan email ada di AUTHORIZED_EMAILS |
| JWT token invalid | Pastikan JWT_SECRET_KEY sama di semua instance, cek expiry token |

**Troubleshooting IDCloudHost:**

| Masalah | Solusi |
|---------|--------|
| SSH connection refused | Tunggu 2-3 menit setelah server dibuat, atau restart server di dashboard IDCloudHost |
| Password tidak bekerja | Password case-sensitive. Paste ulang dari email, jangan ketik manual |
| Permission denied | Pastikan login sebagai `root`, bukan user lain |
| Server lambat | Upgrade plan atau ganti lokasi ke Jakarta di IDCloudHost |
| Tidak bisa membuat server (insufficient balance) | Top-up saldo di **Billing** → **Top Up Balance** |
| Server hilang/tidak terlihat | Cek apakah saldo habis (server auto-delete jika tidak ada saldo) |

**Buka port firewall:**
```bash
sudo ufw allow 8000
sudo ufw allow 22
sudo ufw enable
```

---

## Quick Reference (Cheat Sheet)

### Command Penting di Server

```bash
# Cek versi sistem
uname -a
lsb_release -a

# Cek penggunaan disk
df -h

# Cek penggunaan RAM
free -h

# Cek list proses Python
ps aux | grep python

# Kill process tertentu
kill -9 <PID>

# Cek port yang listening
sudo netstat -tlnp | grep LISTEN

# Update semua package
sudo apt update && sudo apt upgrade -y

# Monitor real-time resource
htop

# Cek size folder
du -sh /home/bot-trading-mythos
```

### Database Commands

```bash
# Login ke MySQL
mysql -u root -p

# List databases
SHOW DATABASES;

# Gunakan database
USE bot_trading_mythos;

# List tables
SHOW TABLES;

# Check table structure
DESC trades;

# Backup database
mysqldump -u root -p bot_trading_mythos > backup.sql

# Restore database
mysql -u root -p bot_trading_mythos < backup.sql
```

### Bot Commands

```bash
# Start bot (manual)
source /home/bot-trading-mythos/venv/bin/activate
python /home/bot-trading-mythos/scripts/run_bot.py

# Start via systemd
sudo systemctl start mythos-bot

# Stop bot
sudo systemctl stop mythos-bot

# Restart bot
sudo systemctl restart mythos-bot

# View logs
journalctl -u mythos-bot -f

# View past logs (last 100 lines)
journalctl -u mythos-bot -n 100
```

---

## Penting

- **Default mode adalah PAPER TRADING** - tidak menggunakan uang asli
- Untuk switch ke LIVE mode, ubah via dashboard atau `.env` → `TRADING_MODE=live`
- **JANGAN** enable withdrawal permission di Binance API
- Selalu test di paper mode sebelum live trading
- Bot ini bukan jaminan profit - selalu gunakan risk management yang baik
- **Backup database regularly** - sebelum update atau perubahan besar

---

## API Endpoints

| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| GET | `/` | - | Dashboard |
| GET | `/health` | - | Health check basic |
| GET | `/auth/login` | - | Google OAuth login URL |
| POST | `/auth/google/callback` | - | OAuth code exchange → JWT |
| GET | `/auth/me` | JWT | Info user yang login |
| POST | `/auth/logout` | JWT | Logout |
| GET | `/api/health/status` | JWT | Health monitoring lengkap |
| GET | `/api/health/ping` | - | Health ping |
| GET | `/api/stats` | JWT | Statistik overview |
| GET | `/api/balance` | JWT | Balance info |
| GET | `/api/positions` | JWT | Open positions |
| GET | `/api/trades` | JWT | Trade history |
| GET | `/api/signals` | JWT | Signal history |
| GET | `/api/performance` | JWT | Performance metrics |
| GET | `/api/logs` | JWT | System logs |
| GET | `/api/strategies` | JWT | Available strategies |
| POST | `/api/bot/start` | JWT | Start bot |
| POST | `/api/bot/stop` | JWT | Stop bot |
| POST | `/api/bot/mode` | JWT | Set mode (paper/live) |
| POST | `/api/strategy/set` | JWT | Set strategy |
| POST | `/api/emergency/clear` | JWT | Clear emergency stop |
| POST | `/api/backtest/run` | JWT | Run backtest |
| GET | `/api/backtest/results` | JWT | Get backtest results |
| GET | `/docs` | - | API documentation (Swagger) |
