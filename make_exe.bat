:: DO NOT DOUBLE-CLICK THIS BATCH FILE TO RUN IT!!!!
:: You must start a command prompt and execute it.

set ZIPLINE_DIR=.\src\cmd\zipline

mkdir %ZIPLINE_DIR%
xcopy .\..\..\zipline %ZIPLINE_DIR% /E
:: "pyinstaller" --clean --noconfirm --upx-dir .\src\misc\upx-5.0.2-win64 zipline-gui.spec
"pyinstaller" --clean --noconfirm --upx-dir .\src\misc\upx-5.0.2-win64 zipline-gui.spec

rmdir %ZIPLINE_DIR% /s /q
copy .\src\cmd\zipline-gui.bat .\dist\zipline-gui\zipline-gui.bat
