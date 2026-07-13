# Known Problems & Research Items

## Gemini "bắt máy" (SIP callee) trên LiveKit Cloud

### Vấn đề

Outbound SIP (`outbound_sip`) hiện tại: `call_to` = **DID của agent** → agent join room → bridge audio → Gemini nói chuyện được.

Nhưng nếu gọi **số điện thoại thật** (PSTN):

```
lk-sim dial +84xxxxxxxxx  ──►  Cloud Trunk  ──►  PSTN  ──►  Máy thật reo
                                                          │
                                                        Người nhấc máy
                                                          │
                                                        Worker nghe người, 
                                                        Gemini không nghe ai
```

Gemini chỉ "bắt máy" được khi cuộc gọi vào **room có Gemini**. Trên Cloud:
- Agent có inbound DID + dispatch rule → agent-room
- Gemini cần **inbound DID riêng + dispatch rule** → sim-room
- Hiện tại chưa có DID route vào sim-room

### Giải pháp tiềm năng

| Hướng | Mô tả | Cần |
|---|---|---|
| **DID route sim-room** | Mua số/DID + dispatch rule trỏ sim-room | Provisioning LiveKit |
| **Self-host SIP + sip-to-ai** | LiveKit SIP docker local + in-process callee | Docker + vendored `sip-to-ai` |
| **Twilio SIP trunk hairpin** | Dùng Twilio routing quay vào sim-room | Twilio config |

### Liên quan

- `docs/plans/PLAN-20260713-simleg-refactor.md` (T6 vendor sip-to-ai)
- `docs/telephony.md`
- `references/sip-to-ai/` (clone tham khảo, Apache-2.0)
