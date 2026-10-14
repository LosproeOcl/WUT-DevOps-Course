# Cars CRUD 容器化命令速查表

## 一、构建镜像

```bash
# 标准构建（基础镜像来自 Docker Hub）
docker build -t cars-crud:local .

# 国内网络走课程 Azure 代理构建（基础镜像换源，不改 Dockerfile）
docker build --build-arg BASE_IMAGE=efreiwut.azurecr.io/dockerhub/library/python:3.12-slim -t cars-crud:local .
```

## 二、运行容器

```bash
docker run -d --name cars-app -p 127.0.0.1:8000:8000 \
  --mount type=volume,source=cars-data,target=/data cars-crud:local
```

- `-d` 后台运行
- `--name cars-app` 命名容器
- `-p 127.0.0.1:8000:8000` 端口映射（宿主机:容器，只绑本机）
- `--mount type=volume,source=cars-data,target=/data` 挂载命名卷持久化 SQLite

## 三、验证数据持久化

```bash
docker stop cars-app
docker rm cars-app
docker run -d --name cars-app -p 127.0.0.1:8000:8000 \
  --mount type=volume,source=cars-data,target=/data cars-crud:local
```

删除容器后卷仍在，重新运行数据不丢。

## 四、CLI 速查表

| 命令 | 作用 |
|---|---|
| `docker build -t cars-crud:local .` | 根据 Dockerfile 构建镜像 |
| `docker image ls` | 列出本地镜像 |
| `docker ps` | 列出运行中的容器 |
| `docker ps -a` | 列出全部容器（含已停止） |
| `docker logs cars-app` | 查看容器日志 |
| `docker logs -f cars-app` | 实时跟踪日志（Ctrl+C 停止） |
| `docker stop cars-app` | 停止运行中的容器 |
| `docker start cars-app` | 重新启动已停止的容器 |
| `docker rm cars-app` | 删除已停止的容器（不删命名卷） |
| `docker volume ls` | 列出命名卷 |
| `docker exec -it cars-app sh` | 进入容器内部 shell |
| `docker exec cars-app <命令>` | 在容器内执行单条命令 |
| `docker tag 源 目标` | 给镜像起另一个名称/标签 |
| `docker push 镜像` | 上传镜像到注册表 |
| `docker pull 镜像` | 从注册表下载镜像 |

## 五、发布到 Docker Hub

```bash
# 1. 登录（密码粘贴个人访问令牌，不是 GitHub 密码）
docker login --username YOUR_DOCKER_ID

# 2. 打标签（v1 和 latest）
docker tag cars-crud:local YOUR_DOCKER_ID/cars-crud:v1
docker tag cars-crud:local YOUR_DOCKER_ID/cars-crud:latest

# 3. 推送
docker push YOUR_DOCKER_ID/cars-crud:v1
docker push YOUR_DOCKER_ID/cars-crud:latest

# 4. 别人（或另一台机器）拉取并运行
docker pull YOUR_DOCKER_ID/cars-crud:latest
docker run -d --name cars-from-hub -p 127.0.0.1:8000:8000 \
  --mount type=volume,source=cars-from-hub-data,target=/data YOUR_DOCKER_ID/cars-crud:latest
```

> 注意：`docker login` 密码填 **Docker Hub 个人访问令牌**（Personal access token，在 Account settings > Personal access tokens 生成，权限选 Repo Read & Write），不要用 GitHub 密码，也不要把它写进 Dockerfile/Git/截图。

## 六、本次实际操作记录（Docker ID: lospr）

```bash
# 1. 登录（令牌经 stdin 传入，避免出现在 shell 历史；实际令牌已打码）
<令牌> | docker login -u lospr --password-stdin
# → Login Succeeded

# 2. 打标签
docker tag cars-crud:local lospr/cars-crud:v1
docker tag cars-crud:local lospr/cars-crud:latest

# 3. 推送
docker push lospr/cars-crud:v1
# → v1: digest: sha256:e5579b13c94f2b6d1bc490e2fd29369ee654a6e01c76aa7d703c717ad47842ac size: 856

docker push lospr/cars-crud:latest
# → latest: digest: sha256:e5579b13...（层已存在，直接复用，秒传）
```

**结果：** 已发布到 Docker Hub
- `lospr/cars-crud:v1`
- `lospr/cars-crud:latest`

仓库地址：https://hub.docker.com/repository/docker/lospr/cars-crud

**观察点：** `latest` 推送几乎瞬间完成，因为 `v1` 已上传全部层，`latest` 只是同一镜像的另一个标签，层直接复用（"Layer already exists"）。

## 七、Docker 卷（Volumes）—— 命名卷与持久化

**为什么需要卷：** 容器的可写文件系统层会随容器删除而销毁，重要数据（数据库、上传文件）应放在独立于容器的「卷」中。

```bash
# 显式创建命名卷（幂等；首次使用也会自动创建）
docker volume create cars-data

# 查看卷
docker volume ls

# 运行容器并挂载命名卷（source=卷名，target=容器内挂载点）
docker run -d --name cars-app -p 127.0.0.1:8000:8000 \
  --mount type=volume,source=cars-data,target=/data cars-crud:local

# 停止 + 删除容器（rm 不删卷，数据保留）
docker stop cars-app
docker rm cars-app

# 检查卷的配置与挂载位置
docker volume inspect cars-data
# 查看容器的 Mounts 部分
docker inspect cars-app
```

**卷相关命令速查：**

| 命令 | 作用 |
|---|---|
| `docker volume create NAME` | 创建命名卷 |
| `docker volume ls` | 列出卷 |
| `docker volume inspect NAME` | 检查卷的配置和挂载位置 |
| `docker volume rm NAME` | 删除卷（需先删除使用它的容器） |
| `docker volume prune` | 删除未使用的本地卷（可能具破坏性） |
| `docker run --mount type=volume,source=NAME,target=/data ...` | 挂载命名卷 |
| `docker run -v NAME:/data ...` | 挂载命名卷的简短写法 |
