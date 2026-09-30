# Configuration Files - What's What

## `.env` (YOUR ACTUAL CONFIG - PRIVATE!)
- Contains **all your real EZStreet team credentials**
- **NEVER commit this to git** - it's in `.gitignore`
- This is what the bot actually uses

## `.env.example` (TEMPLATE - SAFE TO SHARE)
- Generic placeholders for documentation
- Safe to commit to git and share publicly
- Shows others what variables they need

## `.env.backup.old` (BACKUP)
- Your old messy config saved just in case
- Can delete once you verify everything works

## Summary
✅ **`.env`** = Your real EZStreet secrets (protected by `.gitignore`)  
✅ **`.env.example`** = Public template with fake values  
✅ **`.gitignore`** = Prevents accidental commits of secrets
