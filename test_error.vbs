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

On Error Resume Next
WshShell.Run cmd, 1, False
If Err.Number <> 0 Then
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set f = fso.CreateTextFile("C:\LocalAI_Workstation\vbs_error.txt", True)
    f.WriteLine "Error: " & Err.Description & " | Code: " & Hex(Err.Number)
    f.Close
End If
On Error GoTo 0
