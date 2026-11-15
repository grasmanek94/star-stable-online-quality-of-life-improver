option casemap:none
EXTERN g_originals:QWORD
EXTERN ProxyHideActor:PROC
EXTERN ProxyHideVisual:PROC
EXTERN ProxyHideFlag:PROC
.code
PUBLIC HideHook_0
HideHook_0 PROC
sub rsp,028h
call QWORD PTR [g_originals+00h]
test al,al
jnz SSO5_h1_return
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,080h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rsi
call ProxyHideActor
test eax,eax
jz SSO5_h1_done
mov byte ptr [rsp+0B0h],01h
SSO5_h1_done:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,080h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
SSO5_h1_return:
add rsp,028h
ret 
HideHook_0 ENDP
PUBLIC HideHook_1
HideHook_1 PROC
sub rsp,028h
call QWORD PTR [g_originals+08h]
test al,al
jnz SSO5_h2_return
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,080h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rsi
call ProxyHideActor
test eax,eax
jz SSO5_h2_done
mov byte ptr [rsp+0B0h],01h
SSO5_h2_done:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,080h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
SSO5_h2_return:
add rsp,028h
ret 
HideHook_1 ENDP
PUBLIC HideHook_2
HideHook_2 PROC
sub rsp,028h
call QWORD PTR [g_originals+010h]
test al,al
jnz SSO5_h3_return
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,080h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rbx
call ProxyHideActor
test eax,eax
jz SSO5_h3_done
mov byte ptr [rsp+0B0h],01h
SSO5_h3_done:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,080h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
SSO5_h3_return:
add rsp,028h
ret 
HideHook_2 ENDP
PUBLIC HideHook_3
HideHook_3 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rdi
call ProxyHideActor
test eax,eax
jz SSO5_h4_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h4_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+018h]
HideHook_3 ENDP
PUBLIC HideHook_4
HideHook_4 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rdi
call ProxyHideActor
test eax,eax
jz SSO5_h5_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h5_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+020h]
HideHook_4 ENDP
PUBLIC HideHook_5
HideHook_5 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rdi
call ProxyHideActor
test eax,eax
jz SSO5_h6_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h6_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+028h]
HideHook_5 ENDP
PUBLIC HideHook_6
HideHook_6 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rdi
call ProxyHideActor
test eax,eax
jz SSO5_h7_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h7_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+030h]
HideHook_6 ENDP
PUBLIC HideHook_7
HideHook_7 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,09h
call ProxyHideFlag
test eax,eax
jz SSO5_h8_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h8_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+038h]
HideHook_7 ENDP
PUBLIC HideHook_8
HideHook_8 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,09h
call ProxyHideFlag
test eax,eax
jz SSO5_h9_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h9_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+040h]
HideHook_8 ENDP
PUBLIC HideHook_9
HideHook_9 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,09h
call ProxyHideFlag
test eax,eax
jz SSO5_h10_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h10_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+048h]
HideHook_9 ENDP
PUBLIC HideHook_10
HideHook_10 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,08h
call ProxyHideFlag
test eax,eax
jz SSO5_h11_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h11_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+050h]
HideHook_10 ENDP
PUBLIC HideHook_11
HideHook_11 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,07h
call ProxyHideFlag
test eax,eax
jz SSO5_h12_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h12_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+058h]
HideHook_11 ENDP
PUBLIC HideHook_12
HideHook_12 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rcx
call ProxyHideVisual
test eax,eax
jz SSO5_h13_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h13_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+060h]
HideHook_12 ENDP
PUBLIC HideHook_13
HideHook_13 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,0Ah
call ProxyHideFlag
test eax,eax
jz SSO5_h14_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h14_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+068h]
HideHook_13 ENDP
PUBLIC HideHook_14
HideHook_14 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,0Ah
call ProxyHideFlag
test eax,eax
jz SSO5_h15_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h15_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+070h]
HideHook_14 ENDP
PUBLIC HideHook_15
HideHook_15 PROC
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,088h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov ecx,0Ah
call ProxyHideFlag
test eax,eax
jz SSO5_h16_pass
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
ret 
SSO5_h16_pass:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,088h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
jmp QWORD PTR [g_originals+078h]
HideHook_15 ENDP
PUBLIC HideHook_16
HideHook_16 PROC
sub rsp,028h
call QWORD PTR [g_originals+080h]
test al,al
jz SSO5_h17_return
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,080h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rcx
call ProxyHideVisual
test eax,eax
jz SSO5_h17_done
mov byte ptr [rsp+0B0h],00h
SSO5_h17_done:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,080h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
SSO5_h17_return:
add rsp,028h
ret 
HideHook_16 ENDP
PUBLIC HideHook_17
HideHook_17 PROC
sub rsp,028h
call QWORD PTR [g_originals+088h]
test al,al
jz SSO5_h18_return
pushfq 
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp,080h
movdqu [rsp+020h],xmm0
movdqu [rsp+030h],xmm1
movdqu [rsp+040h],xmm2
movdqu [rsp+050h],xmm3
movdqu [rsp+060h],xmm4
movdqu [rsp+070h],xmm5
mov rcx,rcx
call ProxyHideVisual
test eax,eax
jz SSO5_h18_done
mov byte ptr [rsp+0B0h],00h
SSO5_h18_done:
movdqu xmm0,[rsp+020h]
movdqu xmm1,[rsp+030h]
movdqu xmm2,[rsp+040h]
movdqu xmm3,[rsp+050h]
movdqu xmm4,[rsp+060h]
movdqu xmm5,[rsp+070h]
add rsp,080h
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq 
SSO5_h18_return:
add rsp,028h
ret 
HideHook_17 ENDP
END
