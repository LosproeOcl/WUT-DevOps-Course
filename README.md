# DevOps & MLOps 璇剧▼璁板綍

- 鏈哄櫒锛歐indows 11锛圔uild 10.0.26200锛?- 鐢ㄦ埛锛歽qysperiod\19284

## 涓€銆佺幆澧?
| 缁勪欢 | 鐗堟湰 | 鐘舵€?|
|---|---|---|
| Python | 3.12.0 | 鉁?|
| Git | 2.55.0.windows.5 | 鉁?|
| Docker Desktop | 4.94.0锛圗ngine 29.8.2锛學SL2 鍚庣锛?| 鉁?|
| JupyterLab | 4.6.4 | 鉁?|
| MLflow | 3.17.0 | 鉁?|
| DVC | 3.67.1 | 鉁?|
| Flask | 3.1.3 | 鉁?|
| FastAPI / uvicorn | 0.136.3 / 0.48.0 | 鉁?|
| scikit-learn | 1.9.1 | 鉁?|
| GitHub | LosproeOcl锛坓h CLI 2.100.0锛?| 鉁?|
| DagsHub | losproeocl | 鉁?|
| Azure | 瀛︾敓璐﹀彿锛?100 棰濆害锛孊lob 瀛樺偍锛?| 鉁?|

## 浜屻€佺洰褰曠粨鏋?
```
Devops&MLOps/
鈹溾攢鈹€ finalProject/        # 鏈熸湯椤圭洰锛堢嫭绔嬪垎鏀?main锛?鈹溾攢鈹€ LearningDoc/         # 瀛︿範鏂囨。
鈹溾攢鈹€ Config/              # 鐜閰嶇疆锛坙ogs/銆乻cripts/锛?鈹溾攢鈹€ Note/                # 璇惧爞绗旇
鈹溾攢鈹€ PracticeIntro/       # 缁冧範鎸囧崡锛圥DF锛屽惈涓枃鐗堬級
鈹溾攢鈹€ PowerPoint/          # 璇句欢
鈹溾攢鈹€ Quiz_recap/          # 娴嬮獙鍥為【
鈹溾攢鈹€ cars-crud/           # 缁冧範椤圭洰锛堢嫭绔嬪垎鏀?cars-crud锛?鈹溾攢鈹€ git-playground/      # 缁冧範椤圭洰锛堢嫭绔嬪垎鏀級
鈹斺攢鈹€ data/                # DVC 鏁版嵁
```

## 涓夈€佹湡鏈」鐩?
**鏂归潰绾ф儏鎰熷垎鏋?*锛坄finalProject/`锛屽垎鏀?`main`锛?
- 杈撳叆涓枃椁愬巺璇勮锛岃緭鍑哄彛鍛?/ 鏈嶅姟 / 浠锋牸 / 鐜鍥涗釜缁村害鐨勬璐熸儏鎰?- FastAPI 搴旂敤锛氬垎鏋?+ 鍘嗗彶涓や釜椤甸潰锛屼腑鑻卞弻璇晫闈?- 涓変釜鍙€夋ā鍨嬶細TF-IDF + LR锛堥粯璁わ級銆丅ERT銆丷oBERTa
- CSV 鎵归噺瀵煎叆瀵煎嚭銆佷繚瀛樿褰?CRUD锛圫QLite锛?- DVC 鏁版嵁鐗堟湰绠＄悊锛圓zure Blob 杩滅锛夈€丮Lflow 瀹為獙璺熻釜涓庢ā鍨嬫敞鍐岋紙DagsHub锛?- Docker + GitHub Actions CI/CD
- Release锛?https://github.com/LosproeOcl/WUT-DevOps-Course/releases/tag/v1.0.0>
- 璇﹁ `finalProject/README.md`銆乣finalProject/README_zh.md`

## 鍥涖€佺増鏈竻鍗?
| 缁勪欢 | 鐗堟湰 |
|---|---|
| Python | 3.12.0 |
| Git | 2.55.0.windows.5 |
| Docker CLI / Engine | 29.8.2 |
| Docker Desktop | 4.94.0 |
| Docker Compose | v5.5.1 |
| WSL | 3.0.1锛堝唴鏍?6.18.40.1-1锛?|
| JupyterLab | 4.6.4 |
| MLflow | 3.17.0 |
| DVC | 3.67.1 |
| Flask | 3.1.3 |
| FastAPI | 0.136.3 |
| uvicorn | 0.48.0 |
| scikit-learn | 1.9.1 |
| GitHub CLI (gh) | 2.100.0 |

## 浜斻€佹棩蹇椾笌鑴氭湰

- 鏃ュ織鐩綍 `Config/logs/`锛歱ip / docker / wsl 瀹夎鏃ュ織
- 鑴氭湰鐩綍 `Config/scripts/`锛歚check-env.ps1`锛堢幆澧冭嚜妫€锛夈€乣install-wsl.ps1`锛圵SL2 鎻愭潈瀹夎锛?