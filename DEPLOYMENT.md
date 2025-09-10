# Deployment Guide 🚀

This guide covers deploying the Ice Skate Sharpening Ticket System to production.

## Railway Deployment (Recommended)

Railway is the easiest platform for deploying this application with automatic HTTPS, database, and GitHub integration.

### Step 1: Prepare Your Accounts

1. **GitHub Account**: Ensure your code is pushed to GitHub
2. **Railway Account**: Sign up at [railway.app](https://railway.app) using your GitHub account
3. **GatewayAPI Account**: Sign up at [gatewayapi.eu](https://gatewayapi.eu) for SMS services
4. **Stripe Account**: Create account at [stripe.com](https://stripe.com) and enable MobilePay

### Step 2: Deploy to Railway

1. **Connect GitHub**:
   - Go to [railway.app](https://railway.app)
   - Click "Deploy from GitHub repo"
   - Select `osandum/skate-sharpening-tickets`

2. **Add Database**:
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set the `DATABASE_URL` environment variable

3. **Configure Environment Variables**:
   ```bash
   # Required Variables
   SECRET_KEY=generate-a-32-character-random-string
   FLASK_ENV=production
   BASE_URL=https://your-app-name.railway.app

   # SMS Service
   GATEWAYAPI_TOKEN=your-gatewayapi-token

   # Payment Processing
   STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key
   STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable-key
   ```

4. **Deploy**:
   - Railway automatically builds and deploys using your Dockerfile
   - Your app will be available at `https://your-app-name.railway.app`

### Step 3: Initial Setup

1. **Create Admin Account**:
   - Visit `https://your-app-name.railway.app/admin/create_sharpener`
   - Create accounts for your sharpeners

2. **Test SMS Integration**:
   - Create a test ticket to verify SMS delivery
   - Check GatewayAPI dashboard for message status

3. **Configure Stripe Webhook**:
   - In Stripe dashboard, add webhook endpoint: `https://your-app-name.railway.app/payment_success`
   - Add required events for payment confirmation

## Alternative Deployment Options

### DigitalOcean App Platform

1. **Create App**:
   - Connect GitHub repository
   - Choose "Docker" as build method
   - Set environment variables in dashboard

2. **Add Database**:
   - Add PostgreSQL database component
   - Configure connection string

### Fly.io

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Initialize and Deploy**:
   ```bash
   fly launch
   fly postgres create
   fly postgres attach <database-name>
   fly deploy
   ```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session security | Random 32+ character string |
| `BASE_URL` | Public URL of your app | `https://yourdomain.com` |
| `GATEWAYAPI_TOKEN` | SMS service token | From GatewayAPI dashboard |
| `STRIPE_SECRET_KEY` | Payment processing | `sk_live_...` from Stripe |
| `STRIPE_PUBLISHABLE_KEY` | Payment processing | `pk_live_...` from Stripe |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection | PostgreSQL auto-configured |
| `FLASK_ENV` | Environment mode | `production` |
| `DEBUG` | Debug mode | `false` |

## Production Checklist

### Security
- [ ] Generate strong `SECRET_KEY` (32+ characters)
- [ ] Use HTTPS (automatic with Railway/DigitalOcean)
- [ ] Set `FLASK_ENV=production`
- [ ] Keep API keys in environment variables only

### SMS Integration
- [ ] GatewayAPI account created and funded
- [ ] Test SMS delivery to Danish numbers
- [ ] Verify SMS sender name shows as "SkateSharp"

### Payment Processing
- [ ] Stripe account verified and activated
- [ ] MobilePay enabled in Stripe dashboard
- [ ] Test payments in Stripe test mode first
- [ ] Configure webhooks for payment confirmation

### Database
- [ ] PostgreSQL database provisioned
- [ ] Database connection string configured
- [ ] Initial sharpener accounts created

### Monitoring
- [ ] Application health checks passing
- [ ] Database backup strategy in place
- [ ] Error monitoring configured (optional)

## Troubleshooting

### Common Issues

**App won't start**:
- Check environment variables are set correctly
- Verify database connection string
- Check Railway/platform logs for errors

**SMS not sending**:
- Verify GatewayAPI token is correct
- Check phone number format (+45 for Denmark)
- Ensure GatewayAPI account has sufficient credits

**Payments failing**:
- Confirm Stripe keys match environment (test vs live)
- Verify MobilePay is enabled in Stripe
- Check Stripe webhook configuration

**Database errors**:
- Ensure PostgreSQL database is running
- Check DATABASE_URL format
- Verify database migrations completed

## Scaling Considerations

### Traffic Growth
- **Railway**: Automatically scales based on traffic
- **DigitalOcean**: Increase app size or add replicas
- **Custom**: Use load balancer with multiple instances

### Database Performance
- Monitor connection pool usage
- Consider read replicas for high traffic
- Implement database connection pooling

### SMS Rate Limits
- GatewayAPI has rate limits - contact support for high volume
- Consider SMS queuing for peak times
- Monitor SMS delivery rates and costs

## Backup Strategy

### Database Backups
- **Railway**: Automatic daily backups included
- **DigitalOcean**: Configure automatic backups
- **Manual**: Use `pg_dump` for PostgreSQL backups

### Application Backup
- Code is backed up in GitHub repository
- Environment variables documented in deployment
- Database schema documented in README.md

## Support

For deployment issues:
1. Check platform documentation (Railway, DigitalOcean, Fly.io)
2. Review application logs for error messages
3. Verify all environment variables are set correctly
4. Test integrations (SMS, payments) separately

For application-specific issues, open a GitHub issue with deployment details.
