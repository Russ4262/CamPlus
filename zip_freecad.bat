REM Zip all folders of FreeCAD install directory into single archive
set root=%~dp0

REM tar.exe --help
REM "C:\Program Files\7-Zip\7z.exe" --help

"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\bin
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\data
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\doc
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\Ext
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\include
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\lib
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\Mod
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\resources
"C:\Program Files\7-Zip\7z.exe" a -t7z FreeCAD_git_.7z %ROOT%\translations

pause