REM Zip individual folders of FreeCAD install directory
REM cd C:\Users\Public\Documents\FreeCAD_Install
set root=%~dp0

REM tar.exe --help
REM "C:\Program Files\7-Zip\7z.exe" --help

"C:\Program Files\7-Zip\7z.exe" a -t7z bin.7z %ROOT%\bin
"C:\Program Files\7-Zip\7z.exe" a -t7z data.7z %ROOT%\data
"C:\Program Files\7-Zip\7z.exe" a -t7z doc.7z %ROOT%\doc
"C:\Program Files\7-Zip\7z.exe" a -t7z Ext.7z %ROOT%\Ext
"C:\Program Files\7-Zip\7z.exe" a -t7z include.7z %ROOT%\include
"C:\Program Files\7-Zip\7z.exe" a -t7z lib.7z %ROOT%\lib
"C:\Program Files\7-Zip\7z.exe" a -t7z Mod.7z %ROOT%\Mod
"C:\Program Files\7-Zip\7z.exe" a -t7z resources.7z %ROOT%\resources
"C:\Program Files\7-Zip\7z.exe" a -t7z translations.7z %ROOT%\translations

pause