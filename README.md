# 2024 Winter Wheel Seminar Final Assignment

휠 세미나 최종 과제에서는 휠 세미나 전반에서 배운
지식들을 활용하여 서비스를 배포하게 됩니다.

# Requisites
이 과제에서는 다음과 같은 기능들을 구현하게 됩니다.

- [ ] **[`app.py`](./app.py)를 작동시키는 `Dockerfile`을 작성**
    - Docker
- [ ] **[`app.py`](./app.py)와 mysql 데이터베이스, `nginx` 리버스 프록시로 구성된 
`docker-compose.yml` 작성**
    - Docker
    - NginX
- [ ] **AWS의 `EC2`와 `S3`을 이용하여 서비스를 배포할 수 있는 환경 구성**
    - AWS
    - Linux
    - etwork & DNS
- [ ] **`EC2`에 배포된 서비스를 `HTTPS`로 접속할 수 있도록 `ssl` 인증서 발급**
    - Network & DNS
    - Apache & NginX
- [ ] (optional) **Shell script와 crontab을 이용하여 데이터베이스를 주기적으로 백업**
    - Linux

![Overview](./overview.png)

# Guide
최종 과제를 구현하기 위한 가이드입니다. 
어디까지나 가이드일 뿐이며, 꼭 **가이드에 나온 방법, 툴을 사용하지 않아도 무방**합니다. 

## 1. `Dockerfile` 작성
이 과제에서는 [`app.py`](./app.py)를 작동시키는 `Dockerfile`을 작성해야 합니다.

`Dockerfile` 안에서는 다음과 같은 작업을 수행해야 합니다. 

[`./Dockerfile`](./Dockerfile)
- [ ] `pip install -r requirements.txt`으로 디펜던시 설치
- [ ] `python3 app.py`로 서버 실행

베이스 이미지로는 클라이언트와 서버 모두 [`python:3.11-bullseye`](https://hub.docker.com/_/python) 이미지, 또는 이를 베이스로 하는 이미지를 사용하면 됩니다. 

## 2. `docker-compose.yml` 작성
[`docker-compose.yml`](./docker-compose.yml) 파일을 작성하여 클라이언트, 서버, 데이터베이스, 리버스 프록시 컨테이너를 구성하게 됩니다.

### 서버 컨테이너
위에서 작성한 `Dockerfile`을 이용하여 서버 컨테이너를 구성합니다. 
이때 각각의 컨테이너에 필요한 환경 변수들을 설정해 주어야 합니다. 
**서버 포트는 5000번 포트 입니다**

#### 환경 변수
```dotenv
DOMAIN=                  # 서비스 도메인
AWS_ACCESS_KEY_ID=       # AWS Access Key ID
AWS_SECRET_ACCESS_KEY=   # AWS Secret Access Key
AWS_S3_BUCKET_NAME=      # AWS S3 버킷 이름
AWS_S3_CLOUDFRONT=       # AWS S3 Cloudfront domain name
```

### 데이터베이스

이 레포지토리에서는 `Mysql`을 사용합니다.
[`mysql` 이미지](https://hub.docker.com/_/mysql)를 사용하여 데이터베이스 컨테이너를 구성합니다.

이 이미지의 자세한 사용 방법에 대해서는 [Docker Hub](https://hub.docker.com/_/mysql)을 참고하세요.

### 리버스 프록시

[`nginx` 이미지](https://hub.docker.com/_/nginx)를 사용하여 리버스 프록시 컨테이너를 구성합니다.

`/` 주소로 접속했을 때 static 폴더로, `/api` 주소로 접속했을 때 서버 컨테이너로 프록시를 설정해야 합니다.

`/api`를 통해 접근될 시 백엔드에는 `/`로 접근되도록 해야합니다. 이를 통해 nginx의 rewrite를 사용하셔야 합니다.

Docker의 [Networking](https://docs.docker.com/network/) 기능을 활용하면 서버 컨테이너의 포트를 외부에 노출하지 않고
프록시를 설정할 수 있습니다.

> **HINT** 
> `nginx.conf` 파일을 컨테이너 내부에 적용하기 위해 다음 방법 중 하나를 사용해 볼 수 있습니다. 
> - Volume mount 이용 (/etc/nginx/conf.d/default.conf)
> - 기존 nginx 이미지를 베이스 이미지로 하는 새로운 이미지 빌드


### (optional) 새로 빌드된 이미지 기반으로 EC2의 컨테이너 재시작

> **HINT** 
> `docker-compose.yml` 파일이 이미지 레지스트리에 푸쉬된 이미지를 사용하도록 작성되어 있다면
> `docker-compose up -d --build`을 다시 실행하는 것만으로 서비스를 재배포할 수 있습니다.


## 3. AWS 배포 환경 구성

AWS에 배포하기 위해 `EC2`와 `S3`을 사용해 배포 환경을 구성해 주면 됩니다.

### EC2

클라이언트 컨테이너와 서버 컨테이너, 리버스 프록시 컨테이너와 데이터베이스 컨테이너 모두를 EC2 인스턴스에 배포합니다.

모두 도커화되어 있으므로 EC2 인스턴스에는 **도커 컨테이너를 올릴 수 있는 환경**만 구성해주면 됩니다. 

또한 CI/CD를 위해 설정을 구성해주셔야 합니다. 

### S3

S3는 asset을 업로드하기 위해 사용됩니다. 이를 위해서 권한이 **Restricted**으로 설정된 S3 버킷을 생성해 주시면 됩니다.

### CloudFront

S3와 연결된 CloudFront를 외부 웹 접속에 사용합니다. 이를 위해
권한설정이 따로 필요합니다.

## 4. SSL 인증서

`letsencrypt`에서 SSL 인증서를 발급받아 서비스에 https로 접속할 수 있도록 합니다. 

구현 방법은 자유이며, 가능한 구현 방법 예시로는 다음이 있습니다. 

- `certbot` nginx 플러그인을 사용하여 SSL 인증서 발급
- `certbot` standalone 모드를 사용하여 SSL 인증서 발급
- `certbot` dns 모드를 사용하여 SSL 인증서 발급

## 5. 데이터베이스 백업 설정
> Optional 과제를 수행하는 경우에만 필요한 단계입니다. 

`crontab`을 이용해 주기적으로 Mysql의 덤프 파일을 생성하고 S3에 백업하도록 합니다. 

액세스 권한이 다르게 설정된 별도의 S3 버킷을 생성하고, 백업 및 업로드를 진행하는 스크립트를 작성해주시면 됩니다. 
상세한 구현 방법은 자유입니다. 


# Submission

과제의 내용이 모두 구현된 **Github Repository**와 AWS에 배포된 **서비스의 링크**, 모든 작업을 수행한 후 생성된 **JWT 토큰**을 제출해 주세요.


# Remarks

휠 세미나에서 배운 내용을 모두 활용하는 과제인 만큼, 과제의 난이도가 기존 과제들보다 훨씬 높을 것이라 생각합니다. 

휠 세미나를 통과하기 위한 장벽이라기 보다는, 공부한 내용을 실제로 적용해 보고 이를 조합하여 하나의 서비스를 배포하는 데에 중점을 두었으므로 
과제를 하다 막히거나 궁금한 부분이 있다면 자유롭게 질문해 주세요!

