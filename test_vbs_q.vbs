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
WshShell.LogEvent 0, cmd
