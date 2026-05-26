@rem Gradle wrapper for Windows (minimal; Android Studio / CI will use full wrapper)
@if "%OS%"=="Windows_NT" setlocal
set DIRNAME=%~dp0
if exist "%DIRNAME%gradle\wrapper\gradle-wrapper.jar" (
  java -jar "%DIRNAME%gradle\wrapper\gradle-wrapper.jar" %*
) else (
  echo gradle-wrapper.jar missing. Open project in Android Studio once, or use GitHub Actions build.
  exit /b 1
)
