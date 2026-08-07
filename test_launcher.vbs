Set WshShell = CreateObject("WScript.Shell")
args = ""
For i = 0 To WScript.Arguments.Count - 1
    args = args & "Arg " & i & ": " & WScript.Arguments(i) & vbCrLf
Next
WScript.Echo args
WshShell.Run WScript.Arguments(0), 1, False
