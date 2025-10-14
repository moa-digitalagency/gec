# Environment Variables Configuration

## Required Environment Variables

This application requires several environment variables to function properly. Create a `.env` file in the root directory with the following variables:

### 1. Database Configuration
- **DATABASE_URL** (Required)
  - PostgreSQL database connection string
  - Format: `postgresql://username:password@host:port/database`
  - Example: `postgresql://user:pass@localhost:5432/gec_db`
  - Provided automatically by Replit

### 2. Security & Encryption
- **SESSION_SECRET** (Required)
  - Flask session secret key for secure session management
  - Must be a long random string (32+ characters recommended)
  - Example: `your-super-secret-session-key-here-32chars-min`
  - Provided automatically by Replit

- **GEC_MASTER_KEY** (Critical - Required for Production)
  - Master encryption key for sensitive data (Base64 encoded)
  - Used to encrypt/decrypt sensitive information in the database
  - **IMPORTANT**: If not set, a new key is generated on each restart, making previous encrypted data unrecoverable
  - Generate with: `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`
  - Example: `aB3dE6fG9hI0jK1lM2nO3pQ4rS5tU6vW7xY8zA9bC0d=`

- **GEC_PASSWORD_SALT** (Critical - Required for Production)
  - Salt for password hashing (Base64 encoded)
  - **IMPORTANT**: If not set, a new salt is generated on each restart, making previous password hashes invalid
  - Generate with: `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`
  - Example: `zY9xW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dC8bA7aB6c=`

### 3. Admin Access
- **ADMIN_PASSWORD** (Optional)
  - Default password for the super admin account (sa.gec001)
  - Default if not set: `TempPassword123!`
  - **Recommendation**: Set a strong password for production

### 4. Email Configuration (Optional - for notifications)
- **SMTP_SERVER** (Optional)
  - SMTP server hostname
  - Default: `localhost`
  - Example: `smtp.gmail.com`

- **SMTP_PORT** (Optional)
  - SMTP server port
  - Default: `587`
  - Common values: `587` (TLS), `465` (SSL), `25` (unsecured)

- **SMTP_EMAIL** (Optional)
  - Email address used as sender
  - Default: `noreply@gec.local`
  - Example: `notifications@yourdomain.com`

- **SMTP_PASSWORD** (Optional)
  - Password for SMTP authentication
  - Required if your SMTP server requires authentication

- **SMTP_USE_TLS** (Optional)
  - Enable TLS encryption for SMTP
  - Default: `True`
  - Values: `True` or `False`

## .env File Template

```env
# Database (Provided by Replit)
DATABASE_URL=postgresql://user:password@host:port/database

# Security (Provided by Replit)
SESSION_SECRET=your-super-secret-session-key-here-minimum-32-characters

# Encryption Keys (CRITICAL - Generate once and keep secure)
GEC_MASTER_KEY=generate-with-python-command-base64-32-bytes
GEC_PASSWORD_SALT=generate-with-python-command-base64-32-bytes

# Admin Access (Optional)
ADMIN_PASSWORD=YourSecurePassword123!

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=notifications@yourdomain.com
SMTP_PASSWORD=your-smtp-password
SMTP_USE_TLS=True
```

## Security Best Practices

1. **Never commit `.env` file to version control** - Add it to `.gitignore`
2. **Backup encryption keys securely** - Store `GEC_MASTER_KEY` and `GEC_PASSWORD_SALT` in a secure location
3. **Rotate keys periodically** - Change passwords and keys regularly
4. **Use environment-specific values** - Different keys for development, staging, and production
5. **Restrict access** - Limit who can view production environment variables

## Generating Encryption Keys

Run these commands to generate secure encryption keys:

```bash
# Generate GEC_MASTER_KEY
python -c "import secrets, base64; print('GEC_MASTER_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode())"

# Generate GEC_PASSWORD_SALT
python -c "import secrets, base64; print('GEC_PASSWORD_SALT=' + base64.b64encode(secrets.token_bytes(32)).decode())"
```

Alternatively, use the provided utility script:

```bash
python generate_keys.py
```

Or to view your current environment configuration:

```bash
python show_env_keys.py
```

## Quick Setup

1. Copy the .env template above
2. Generate encryption keys using the Python commands or `python generate_keys.py`
3. Fill in your SMTP details if you want email notifications
4. Save as `.env` in the root directory
5. Restart the application

## Using .env File vs Replit Secrets

### On Replit (Recommended)
- Use the Replit Secrets tab to add environment variables
- Secrets are automatically loaded as environment variables
- No `.env` file needed

### Using .env File
- Create a `.env` file in the root directory
- The application will automatically load variables from this file
- Variables in Replit Secrets take priority over `.env` file
- Useful for local development or non-Replit deployments

## Support

For questions or issues related to environment configuration, please contact your DevOps team.
