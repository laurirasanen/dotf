@echo off

SET dest="C:\hlserver\tf2\tf"

:: plugin
rmdir /s /q "%dest%\addons\source-python\plugins\dotf"
robocopy /s /e ".\addons\source-python\plugins\dotf" "%dest%\addons\source-python\plugins\dotf"

:: config
rmdir /s /q "%dest%\cfg\source-python\dotf"
robocopy /s /e ".\cfg\source-python\dotf" "%dest%\cfg\source-python\dotf"

:: resources
rmdir /s /q "%dest%\resource\source-python\translations\dotf"
rmdir /s /q "%dest%\resource\source-python\events\dotf"
robocopy /s /e ".\resource\source-python\translations\dotf" "%dest%\resource\source-python\translations\dotf"
robocopy /s /e ".\resource\source-python\events\dotf" "%dest%\resource\source-python\events\dotf"

:: sound
rmdir /s /q "%dest%\sound\source-python\dotf"
robocopy /s /e ".\sound\source-python\dotf" "%dest%\sound\source-python\dotf"