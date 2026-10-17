Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = scriptDir & "\.venv\Scripts\python.exe"
serverPy = scriptDir & "\server.py"

shell.CurrentDirectory = scriptDir

' ------------------------------------------------------------
' Check whether Face Attendance is already running
' ------------------------------------------------------------
Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
serverReady = False

On Error Resume Next
http.Open "GET", "http://127.0.0.1:8000/health", False
http.SetTimeouts 1000, 1000, 1000, 1000
http.Send

If Err.Number = 0 Then
    If http.Status = 200 Then
        serverReady = True
    End If
End If

Err.Clear
On Error GoTo 0

' Already running ? just open the application
If serverReady Then
    shell.Run "http://127.0.0.1:8000", 1, False
    WScript.Quit
End If

' ------------------------------------------------------------
' Start Face Attendance server hidden
' ------------------------------------------------------------
If Not fso.FileExists(pythonExe) Then
    MsgBox "Face Attendance could not start." & vbCrLf & vbCrLf & _
           "Python environment was not found.", _
           vbCritical, "Face Attendance"
    WScript.Quit 1
End If

If Not fso.FileExists(serverPy) Then
    MsgBox "Face Attendance could not start." & vbCrLf & vbCrLf & _
           "Server file was not found.", _
           vbCritical, "Face Attendance"
    WScript.Quit 1
End If

shell.Run Chr(34) & pythonExe & Chr(34) & " " & Chr(34) & serverPy & Chr(34), 0, False

' ------------------------------------------------------------
' Wait for actual server health
' ------------------------------------------------------------
serverReady = False

For i = 1 To 30
    On Error Resume Next

    http.Open "GET", "http://127.0.0.1:8000/health", False
    http.SetTimeouts 1000, 1000, 1000, 1000
    http.Send

    If Err.Number = 0 Then
        If http.Status = 200 Then
            serverReady = True
            Exit For
        End If
    End If

    Err.Clear
    On Error GoTo 0

    WScript.Sleep 1000
Next

' ------------------------------------------------------------
' Open application or report failure
' ------------------------------------------------------------
If serverReady Then
    shell.Run "http://127.0.0.1:8000", 1, False
Else
    MsgBox "Face Attendance could not start." & vbCrLf & vbCrLf & _
           "The server did not become ready within 30 seconds." & _
           vbCrLf & vbCrLf & _
           "Please contact the administrator.", _
           vbCritical, "Face Attendance"
End If
