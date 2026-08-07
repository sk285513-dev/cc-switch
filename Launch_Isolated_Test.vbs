Set WshShell = CreateObject("WScript.Shell")
Dim cmd, arg, i
cmd = ""
For i = 0 To WScript.Arguments.Count - 1
    arg = WScript.Arguments(i)
    arg = Replace(arg, """", """""")
    If InStr(arg, " ") > 0 Then
        cmd = cmd & """" & arg & """ "
    Else
        cmd = cmd & arg & " "
    End If
Next
Set fso = CreateObject("Scripting.FileSystemObject")
Set f = fso.CreateTextFile("C:\LocalAI_Workstation\vbs_cmd_dump.txt", True)
f.WriteLine cmd
f.Close
WshShell.Run cmd, 1, False
