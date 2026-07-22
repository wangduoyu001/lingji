!macro NSIS_HOOK_PREINSTALL
  ; The packaged runtime is fixed-name and owner-local. Stop an existing managed
  ; process before replacing files, then remove stale unversioned sidecar files.
  nsExec::ExecToLog 'taskkill /F /IM lingji-core.exe'
  Sleep 400
  Delete "$INSTDIR\lingji-core.exe"
  RMDir /r "$INSTDIR\lingji_core_lib"
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; Uninstall removes application binaries only. LingJi owner data lives outside
  ; $INSTDIR and is intentionally untouched.
  nsExec::ExecToLog 'taskkill /F /IM lingji-core.exe'
  Sleep 400
!macroend
