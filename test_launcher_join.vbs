Set WshShell = CreateObject("WScript.Shell")
Dim cmd
cmd = ""
For i = 0 To WScript.Arguments.Count - 1
    If InStr(WScript.Arguments(i), " ") > 0 Then
        cmd = cmd & """" & WScript.Arguments(i) & """ "
    Else
        cmd = cmd & WScript.Arguments(i) & " "
    End If
Next
WScript.Echo "Joined Command: " & cmd
WshShell.Run cmd, 1, False
