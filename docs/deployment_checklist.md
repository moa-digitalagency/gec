# Deployment Checklist - GEC Mines

## ✅ Pre-Deployment Verification

### 1. Code Quality
- [x] All test files removed
- [x] No debug or development code in production
- [x] Error handling implemented throughout
- [x] Security measures active

### 2. File System
- [x] `/uploads` directory exists and writable
- [x] `/exports` directory exists and writable  
- [x] `/instance` directory for database
- [x] All paths use relative references

### 3. Database
- [x] PostgreSQL configured via DATABASE_URL
- [x] Schema migrations completed
- [x] Indexes created for performance
- [x] Backup system functional

### 4. Security Configuration
- [x] SESSION_SECRET environment variable set
- [x] GEC_MASTER_KEY for encryption
- [x] GEC_PASSWORD_SALT configured
- [x] HTTPS enforced in production
- [x] CSRF protection enabled
- [x] Security headers configured

### 5. Features Verified
- [x] User authentication working
- [x] Mail registration (incoming/outgoing)
- [x] Mandatory file attachments
- [x] Search with full metadata indexing
- [x] SG en copie filter operational
- [x] PDF export functional
- [x] File download working
- [x] Permission system active

## 🚀 Deployment Steps

### For Replit
1. Application auto-configures on startup
2. PostgreSQL database auto-provisioned
3. Use Secrets for environment variables
4. Click Deploy button

### For PythonAnywhere
1. Upload code to `/home/yourusername/gecmines`
2. Configure WSGI file:
```python
import sys
path = '/home/yourusername/gecmines'
if path not in sys.path:
    sys.path.append(path)
from main import app as application
```
3. Set environment variables in `.env`
4. Create directories: `uploads`, `exports`
5. Reload web app

### For Heroku
1. Add `Procfile`:
```
web: gunicorn main:app
```
2. Configure environment variables
3. Add PostgreSQL addon
4. Deploy via Git

### For VPS/Dedicated Server
1. Install dependencies: `pip install -r pyproject.toml`
2. Configure nginx/Apache reverse proxy
3. Setup systemd service for gunicorn
4. Configure SSL certificates
5. Setup automatic backups

## 📋 Post-Deployment

### Immediate Actions
1. [ ] Change default admin password
2. [ ] Configure system parameters
3. [ ] Create departments
4. [ ] Add users with appropriate roles
5. [ ] Test all critical functions
6. [ ] Enable monitoring

### Monitoring
- Check `/logs` for activity
- Monitor disk space for uploads
- Database backup schedule
- Security log review

## 🔧 Troubleshooting

### Common Issues

**File Upload Fails**
- Check `uploads` directory permissions
- Verify max file size settings
- Check disk space

**PDF Export Error**
- Ensure `exports` directory exists
- Check ReportLab installation
- Verify font availability

**Database Connection**
- Confirm DATABASE_URL is correct
- Check PostgreSQL service status
- Verify network connectivity

**Login Issues**
- Clear browser cache
- Check SESSION_SECRET is set
- Verify database user table

## 📞 Support

For deployment assistance:
1. Review application logs
2. Check error messages in browser console
3. Verify all environment variables
4. Ensure all dependencies installed

## ✅ Final Checklist

- [ ] All features tested
- [ ] Security configured
- [ ] Backups scheduled
- [ ] Monitoring active
- [ ] Documentation updated
- [ ] Users trained
- [ ] Go-live approved

---
*Last Updated: August 17, 2025*