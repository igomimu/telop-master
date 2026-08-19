@echo off
title 無音カット (auto-editor)
setlocal

rem ============================================================
rem  囲碁動画から「音も動きも無い区間」を自動カットする
rem
rem  使い方: 動画ファイルをこの .bat のアイコンにドラッグ＆ドロップ
rem          → 同じフォルダに ～_cut.mp4 ができる
rem
rem  同じフォルダに auto-editor.exe を置いておくこと
rem ============================================================

rem --- 調整したいときはここの数字を変える(メモ帳で開けます) ---
set "AUDIO_TH=0.04"
set "MOTION_TH=0.02"
set "MARGIN=1.5sec"
rem   AUDIO_TH  : 音量のしきい値。下げるほど小さい音でも「あり」
rem   MOTION_TH : 画面変化のしきい値。下げるほど残りやすい
rem   MARGIN    : 音/動きの前後に残す長さ(考える間を守る)
rem ------------------------------------------------------------

set "AE=%~dp0auto-editor.exe"
set "EDIT=(or audio:threshold=%AUDIO_TH% motion:threshold=%MOTION_TH%)"

if not exist "%AE%" goto no_exe
if "%~1"=="" goto no_file

:next
set "IN=%~1"
set "OUT=%~dpn1_cut%~x1"

echo.
echo ============================================================
echo  入力: %IN%
echo  判定: %EDIT%  margin=%MARGIN%
echo ============================================================
echo.

if exist "%OUT%" goto skip

echo --- どれだけ縮むか確認中 ---
"%AE%" "%IN%" --edit "%EDIT%" --margin %MARGIN% --preview
if errorlevel 1 goto failed

echo.
echo --- 書き出し中 ---
"%AE%" "%IN%" --edit "%EDIT%" --margin %MARGIN% -o "%OUT%" --no-open
if errorlevel 1 goto failed

echo.
echo  完了: %OUT%
goto done

:skip
echo  すでに %OUT% があります。上書きしないので、先に名前を変えるか消してください
goto done

:failed
echo.
echo  失敗しました。上のメッセージを確認してください
goto done

:done
shift
if not "%~1"=="" goto next

echo.
echo ============================================================
echo  ※ カットは元データを切ります。元の録画ファイルは消さずに残してください
echo  ※ 手順を見せている区間まで消えていたら MOTION_TH を 0.005 に下げて試す
echo ============================================================
echo.
pause
exit /b

:no_exe
echo.
echo  auto-editor.exe が見つかりません
echo  この .bat と同じフォルダに auto-editor.exe を置いてください
echo.
pause
exit /b

:no_file
echo.
echo  動画ファイルをこの .bat のアイコンにドラッグ＆ドロップしてください
echo.
pause
exit /b
