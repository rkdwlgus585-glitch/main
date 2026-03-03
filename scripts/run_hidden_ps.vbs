' Runs a PowerShell script without opening a visible console window.
Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Quit 2
End If

Dim psScriptPath
psScriptPath = WScript.Arguments(0)

Dim i
Dim argText
argText = ""
For i = 1 To WScript.Arguments.Count - 1
    argText = argText & " " & QuoteArg(WScript.Arguments(i))
Next

Dim command
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " & QuoteArg(psScriptPath) & argText

Dim shell
Set shell = CreateObject("WScript.Shell")
shell.Run command, 0, False

Function QuoteArg(value)
    QuoteArg = """" & Replace(CStr(value), """", """""") & """"
End Function
