Set fso = CreateObject("Scripting.FileSystemObject")
Set f = fso.CreateTextFile("C:\LocalAI_Workstation\wscript_args.txt", True)
For i = 0 To WScript.Arguments.Count - 1
    f.WriteLine "Arg " & i & ": " & WScript.Arguments(i)
Next
f.Close
