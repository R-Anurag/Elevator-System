# Production Deployment Guide

## Quick Deploy

```bash
# 1. Create database password secret
openssl rand -base64 32 > secrets/db_password.txt

# 2. Deploy
docker-compose up --build -d

# 3. Verify
curl http://localhost:8000/
curl http://localhost:3000/
```

## Production Features

### Security
- ✅ Database password in Docker secrets
- ✅ PostgreSQL not exposed externally
- ✅ Network isolation (backend/frontend)
- ✅ Non-root user for frontend container

### Performance
- ✅ Multi-stage Docker builds
- ✅ Resource limits on all containers
- ✅ Production-optimized Next.js build

## Resource Limits

| Service | CPU | Memory |
|---------|-----|--------|
| PostgreSQL | 1.0 | 1GB |
| DB Service | 0.5 | 512MB |
| Backend | 1.0 | 1GB |
| Frontend | 0.5 | 512MB |

## Monitoring

```bash
# View logs
docker-compose logs -f

# Check resources
docker stats

# Health checks
curl http://localhost:8000/
```

## Backup

```bash
# Backup database
docker exec elevator-db pg_dump -U elevator_user elevator_db > backup.sql

# Restore database
cat backup.sql | docker exec -i elevator-db psql -U elevator_user -d elevator_db
```

## Scaling

```bash
# Scale backend
docker-compose up -d --scale backend=3
```

For production scaling, use Kubernetes or Docker Swarm with load balancer.

## Security Checklist

- [x] Database password in Docker secrets
- [x] PostgreSQL not exposed externally
- [x] Resource limits configured
- [x] Non-root user for frontend
- [ ] HTTPS/TLS (requires reverse proxy)
- [ ] API authentication
- [ ] Rate limiting
- [ ] CORS restricted to production domain

## Next Steps

1. **Add Reverse Proxy** - Nginx/Traefik for HTTPS
2. **Implement Authentication** - JWT/OAuth
3. **Set Up Monitoring** - Prometheus + Grafana
4. **CI/CD Pipeline** - GitHub Actions
5. **Cloud Deployment** - AWS/Azure/GCP
