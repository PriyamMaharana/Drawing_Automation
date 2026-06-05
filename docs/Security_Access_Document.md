# Security & Access Document

# Security Philosophy

The application shall operate entirely offline.

No cloud services.

No external APIs.

No internet connectivity required.

---

# Data Flow

PDF
↓
Local Processing
↓
Local Output

No data leaves machine.

---

# Authentication

Phase 1:

No login system.

Single user desktop application.

---

# Authorization

Not applicable.

---

# File Security

Input:

PDF

Output:

Excel
Ballooned PDF

Stored locally.

---

# Data Storage

Application Settings:

```text
config/user_settings.yaml
```

Logs:

```text
logs/application.log
```

---

# Privacy

System shall:

NOT upload files

NOT transmit files

NOT store files externally

NOT use cloud AI services

---

# Malware Surface

Restricted to:

- File Read
- File Write

No:

- Network sockets
- Remote execution
- Database connections

---

# Backup Strategy

User-controlled.

Generated files remain inside:

output/

---

# Audit Logging

Record:

Application Start

PDF Processing

Export Operations

System Errors

---