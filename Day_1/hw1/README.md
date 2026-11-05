## 1-1. 정보 조사
먼저 어떻게 스캔할건지를 정했다. 어떤 정보를 스캔 스크립트에 넣을지 알아보고자 터미널에 ros2 topic list --help 를 입력하였다. 결과는 사진과 같다.
<img width="1388" height="1634" alt="Screenshot from 2026-11-06 02-15-09" src="https://github.com/user-attachments/assets/593c1569-0723-4766-b862-aa574f7b46a9" />

-s는 시뮬레이션 시간에 대한 내용이고, 지금은 시뮬레이터를 사용하지 않아 의미없다. -c(토픽 개수), --include-hidden-topics(숨겨진 토픽. 로봇 토픽은 bb로 확실했다.), -v(스캔에서는 이름만 보고 자세한 정보는 다음 과정에서 봤다.)

## 1-2. 스캔 스크립트
<img width="1388" height="1634" alt="Screenshot from 2026-11-06 02-21-21" src="https://github.com/user-attachments/assets/0abd7ed8-c196-48d7-907d-40b6bcbb58a1" />

+ ROS_DOMAIN_ID: 도메인 몇번인지

+ ros2 topic list: 토픽 명령 보여줌

+ --no-daemo--spin-time 4: 캐시(한 번 조사한 결과를 기억해둔다. 이로인해 새로 data가 생기면 못찾는 문제가 있긴 하다.)없이 4초간 직접 찾음

+ -t: 토픽의 타입을 보여줌

+ grep bb_: 결과 중에서 bb_가 들어간 줄을 찾는다.

## 1-3. 스캔 결과

[scan_result.txt](https://github.com/user-attachments/files/34438680/scan_result.txt)

## 2-1. 토픽 조사

