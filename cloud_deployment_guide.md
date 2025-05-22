# Cloud Deployment Guide for Microservices

## 1. High-Level Deployment Architecture

```ascii
                                    [CloudFront/CDN]
                                          ↑
                                          ↓
[Client] → [Route 53] → [Application Load Balancer] → [API Gateway]
                                          ↓
                    ┌────────────────────┼────────────────────┐
                    ↓                    ↓                    ↓
            [Auth Service]        [User Service]       [Other Services]
                    ↓                    ↓                    ↓
            [Service Cache]      [Service Cache]      [Service Cache]
                    ↓                    ↓                    ↓
            [Database Cluster] ← [Message Queue] → [Search Engine]
                    ↓
            [Backup Storage]

[Monitoring & Logging]
    - CloudWatch
    - X-Ray
    - Prometheus
    - Grafana
```

## 2. CI/CD Pipeline Setup

### GitHub Actions Workflow
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Tests
        run: |
          npm install
          npm test
          npm run lint

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker Images
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to EKS
        run: |
          aws eks update-kubeconfig --name $CLUSTER_NAME
          kubectl set image deployment/$DEPLOYMENT_NAME $CONTAINER_NAME=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

## 3. Logging, Monitoring, and Auto-scaling

### Logging Setup
```yaml
# CloudWatch Logs Configuration
resources:
  - name: CloudWatchLogGroup
    type: AWS::Logs::LogGroup
    properties:
      LogGroupName: /microservices/app
      RetentionInDays: 30

# Application Logging
logging:
  level: INFO
  format: json
  handlers:
    - type: cloudwatch
      logGroup: /microservices/app
      stream: ${service.name}
```

### Monitoring Setup
```yaml
# Prometheus Configuration
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: microservices-monitor
spec:
  selector:
    matchLabels:
      app: microservices
  endpoints:
    - port: metrics
      interval: 15s

# Grafana Dashboard
dashboard:
  panels:
    - title: Service Health
      type: graph
      metrics:
        - name: service_health
          query: rate(http_requests_total[5m])
    - title: Error Rate
      type: graph
      metrics:
        - name: error_rate
          query: rate(http_errors_total[5m])
```

### Auto-scaling Configuration
```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: microservices-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: microservices
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## 4. Secure Authentication Mechanism

### JWT-based Authentication
```typescript
// Auth Service Implementation
import jwt from 'jsonwebtoken';
import { createHash } from 'crypto';

class AuthService {
  private readonly JWT_SECRET = process.env.JWT_SECRET;
  private readonly TOKEN_EXPIRY = '1h';

  async generateToken(user: User): Promise<string> {
    const payload = {
      sub: user.id,
      email: user.email,
      roles: user.roles,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600
    };

    return jwt.sign(payload, this.JWT_SECRET);
  }

  async validateToken(token: string): Promise<DecodedToken> {
    try {
      return jwt.verify(token, this.JWT_SECRET) as DecodedToken;
    } catch (error) {
      throw new UnauthorizedError('Invalid token');
    }
  }
}

// API Gateway Middleware
const authMiddleware = async (req: Request, res: Response, next: NextFunction) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      throw new UnauthorizedError('No token provided');
    }

    const decoded = await authService.validateToken(token);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Unauthorized' });
  }
};
```

## 5. Infrastructure as Code (Terraform)

```hcl
# main.tf
provider "aws" {
  region = "us-west-2"
}

# VPC Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "microservices-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-west-2a", "us-west-2b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = true
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "microservices-cluster"
  cluster_version = "1.21"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  node_groups = {
    general = {
      desired_size = 2
      min_size     = 1
      max_size     = 5
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }
  }
}

# RDS Instance
resource "aws_db_instance" "postgres" {
  identifier        = "microservices-db"
  engine           = "postgres"
  engine_version   = "13.4"
  instance_class   = "db.t3.medium"
  allocated_storage = 20
  
  name     = "microservices"
  username = "admin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  multi_az               = true
}
```

## 6. Containerization and Kubernetes

### Containerization Best Practices

#### Multi-stage Dockerfile
```dockerfile
# Build stage
FROM node:16-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:16-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./

# Security hardening
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

EXPOSE 3000
CMD ["npm", "start"]
```

#### Docker Compose for Local Development
```yaml
version: '3.8'
services:
  app:
    build:
      context: .
      target: builder
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Architecture

#### Namespace Structure
```yaml
# namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production

---
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
```

#### Service Configuration
```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: microservices
  namespace: production
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 3000
      protocol: TCP
  selector:
    app: microservices
```

#### Deployment with Rolling Updates
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: microservices
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: microservices
  template:
    metadata:
      labels:
        app: microservices
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
    spec:
      containers:
      - name: microservices
        image: ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
        ports:
        - containerPort: 3000
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /startup
            port: 3000
          failureThreshold: 30
          periodSeconds: 10
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
        - name: tmp-volume
          mountPath: /tmp
      volumes:
      - name: config-volume
        configMap:
          name: app-config
      - name: tmp-volume
        emptyDir: {}
```

#### ConfigMap and Secrets
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  LOG_LEVEL: "info"
  API_TIMEOUT: "30s"
  CACHE_TTL: "3600"

---
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secrets
  namespace: production
type: Opaque
data:
  url: base64_encoded_database_url
  password: base64_encoded_password
```

#### Network Policies
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: microservices-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: microservices
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
```

### Kubernetes Best Practices

1. **Resource Management**
   - Set appropriate resource requests and limits
   - Use Horizontal Pod Autoscaling (HPA)
   - Implement Vertical Pod Autoscaling (VPA)
   - Monitor resource usage

2. **Security**
   - Use non-root users in containers
   - Implement network policies
   - Use secrets for sensitive data
   - Regular security scanning
   - Pod Security Policies

3. **Monitoring and Logging**
   - Implement health checks
   - Use Prometheus for metrics
   - Centralize logs with ELK stack
   - Set up alerts and notifications

4. **Deployment Strategies**
   - Use rolling updates
   - Implement blue-green deployments
   - Canary deployments for testing
   - Automated rollbacks

5. **Storage Management**
   - Use PersistentVolumes for data
   - Implement backup strategies
   - Regular data cleanup
   - Storage class optimization

6. **Service Mesh Integration**
   - Implement Istio or Linkerd
   - Traffic management
   - Security policies
   - Observability

### Container Registry Management

```yaml
# registry-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: registry-secret
  namespace: production
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: base64_encoded_docker_config
```

### Container Security Scanning

```yaml
# security-scan.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: container-scan
  namespace: production
spec:
  schedule: "0 0 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: trivy
            image: aquasec/trivy
            args:
            - image
            - ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
          restartPolicy: OnFailure
```

### Container Resource Optimization

1. **Image Optimization**
   - Use multi-stage builds
   - Minimize layer count
   - Remove unnecessary files
   - Use .dockerignore

2. **Runtime Optimization**
   - Set appropriate JVM options
   - Configure garbage collection
   - Optimize memory usage
   - Use appropriate base images

3. **Network Optimization**
   - Use service mesh
   - Implement circuit breakers
   - Configure timeouts
   - Use connection pooling

## 7. Security Best Practices

1. **Network Security**
   - VPC with private subnets
   - Security groups and NACLs
   - WAF for API Gateway

2. **Data Security**
   - Encryption at rest and in transit
   - Secrets management
   - Regular security audits

3. **Access Control**
   - IAM roles and policies
   - Least privilege principle
   - Regular access reviews

4. **Compliance**
   - Regular security scanning
   - Compliance monitoring
   - Audit logging

## 8. Disaster Recovery

1. **Backup Strategy**
   - Regular database backups
   - Cross-region replication
   - Point-in-time recovery

2. **Recovery Procedures**
   - Automated failover
   - Recovery time objectives
   - Recovery point objectives

3. **Testing**
   - Regular DR testing
   - Automated recovery testing
   - Documentation updates 