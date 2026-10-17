Set shell = CreateObject("WScript.Shell")

scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
serverPy = LCase(scriptDir & "\server.py")

Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set processes = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='python.exe'")

stopped = False

For Each process In processes
    If Not IsNull(process.CommandLine) Then
        commandLine = LCase(process.CommandLine)

        If InStr(commandLine, serverPy) > 0 Then
            shell.Run "taskkill /PID " & process.ProcessId & " /T /F", 0, True
            stopped = True
            Exit For
        End If
    End If
Next

If stopped Then
    WScript.Sleep 500
End If
