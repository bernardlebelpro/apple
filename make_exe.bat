:: DO NOT DOUBLE-CLICK THIS BATCH FILE TO RUN IT!!!!
:: You must start a command prompt and execute it.

:: Remove the __pycache__ directory.
rmdir .\metsearch\__pycache__ /s /q

:: Make copy of source code next to the metsearch script.
set METSEARCH_DIR=.\scripts\metsearch
mkdir %METSEARCH_DIR%
xcopy .\metsearch %METSEARCH_DIR% /E

"pyinstaller" --clean --noconfirm --noconsole --onefile ^
--add-data ".\metsearch\metsearch.ui;metsearch" ^
-i .\icon\themet.ico ^
.\scripts\metsearch-gui

:: Remove the copy of the source code.
rmdir %METSEARCH_DIR% /s /q
