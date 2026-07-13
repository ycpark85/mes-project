# Vendor Portal External Access Plan

## Objective

Expose only the Bohyun outsource workflow to an external vendor device while keeping the internal MES, database, administration APIs, and internal WPF client private.

The vendor-facing workflow is limited to:

- View assigned Bohyun outsource work groups.
- Mark vendor inbound.
- Mark work done.
- Mark shipment.
- Review status and processing history needed for the above flow.

## Target Architecture

```text
Bohyun vendor WPF app
  -> https://vendor-mes.semiindustry.com/api/v1/vendor-portal/...
    -> Cloudflare Free plan
      -> Cloudflare Tunnel
        -> company server cloudflared service
          -> FastAPI backend, internal port only
            -> Vendor portal API
              -> Shared Bohyun outsource service
                -> MES database
```

The existing internal WPF client remains the internal MES client. The vendor app is a separate WPF application with a much smaller feature set.
The company internet line does not have a fixed public IP, so the external access baseline uses Cloudflare Tunnel instead of a static DNS `A` record and firewall port forwarding.

## DNS Plan

Use the existing company domain:

```text
semiindustry.com
```

Create one subdomain for the vendor endpoint:

```text
vendor-mes.semiindustry.com
```

Domain ownership remains with Gabia, but DNS hosting should move to Cloudflare for the vendor portal rollout.

Planned DNS ownership:

```text
Domain purchase/renewal: Gabia
Authoritative DNS: Cloudflare
Vendor hostname: vendor-mes.semiindustry.com
```

Gabia setup:

- Add `semiindustry.com` to a Cloudflare Free account.
- Copy the two Cloudflare nameserver values shown by Cloudflare.
- In Gabia, change only the nameserver values for `semiindustry.com` to the Cloudflare nameservers.
- Do not configure Gabia DNS host records or DNSSEC for the initial rollout.

Cloudflare setup:

- Recreate any existing required DNS records for `semiindustry.com` before switching nameservers.
- Create a Cloudflare Tunnel for the company MES server.
- Publish `vendor-mes.semiindustry.com` through the tunnel to the internal FastAPI or local reverse proxy service.
- Use a single-level subdomain (`vendor-mes`) to avoid advanced certificate requirements.

## Network Boundary

Only the Cloudflare Tunnel should be reachable from outside. The company firewall does not need inbound 443 port forwarding for the vendor portal.

Allowed outbound from the company server:

- `cloudflared` outbound connections to Cloudflare.

Blocked from the internet:

- Database ports.
- RDP 3389.
- FastAPI direct service port.
- Internal MES API paths.
- Development server ports.
- OpenAPI/docs endpoints.
- Firewall/router inbound port forwarding for this vendor portal.

Cloudflare Tunnel should expose only the vendor portal hostname and path needed by the vendor WPF app.

Allowed public paths:

```text
/api/v1/auth/login
/api/v1/vendor-portal/*
/api/v1/health, only if needed for monitoring
```

Blocked reverse proxy paths:

```text
/api/v1/users/*
/api/v1/roles/*
/api/v1/permissions/*
/api/v1/outsource-work-instructions/*
/api/v1/products/*
/api/v1/order-lines/*
/docs
/openapi.json
```

Backend authorization remains mandatory even if the reverse proxy blocks internal paths.

## Recommended Tunnel Model

Use Cloudflare Free plan plus Cloudflare Tunnel for the initial rollout.

Benefits:

- No fixed public IP required.
- No inbound firewall port forwarding required for the vendor portal.
- Cloudflare provides public HTTPS for `vendor-mes.semiindustry.com`.
- The company server initiates an outbound tunnel using `cloudflared`.
- The existing Gabia domain registration can remain at Gabia.

The origin service can be one of:

```text
cloudflared -> http://127.0.0.1:8000
cloudflared -> http://127.0.0.1:8080 local reverse proxy
```

Prefer routing the tunnel to a local reverse proxy only if path allowlisting is needed outside the FastAPI app. Otherwise, route directly to the FastAPI service and rely on FastAPI authorization plus Cloudflare hostname exposure.

## Backend Design

Add a dedicated vendor portal API namespace:

```text
/api/v1/vendor-portal/bohyun-groups
```

Recommended endpoints:

```text
GET  /api/v1/vendor-portal/bohyun-groups
POST /api/v1/vendor-portal/bohyun-groups/{group_id}/inbound
POST /api/v1/vendor-portal/bohyun-groups/{group_id}/work-done
POST /api/v1/vendor-portal/bohyun-groups/ship-batch
```

Do not expose the existing internal outsource-work-instructions router directly to the vendor app.

Refactor the existing Bohyun outsource-management logic into a shared backend service:

```text
Internal WPF API
  -> shared Bohyun outsource service

Vendor portal API
  -> vendor account and partner-scope checks
  -> shared Bohyun outsource service
```

This keeps the status transition rules identical for internal and external users without exposing the broader internal API surface.

## Required Authorization Model

Vendor users must be linked to the vendor partner record. Prefer a separate mapping table over storing vendor-specific fields directly on `users`.

Proposed table:

```text
vendor_user_access
- vendor_user_access_id
- user_id
- partner_id
- is_active
- created_at
- updated_at
```

Every vendor portal API request must verify:

- The authenticated user is active.
- The user has active access to the required vendor partner.
- The requested work group belongs to the permitted Bohyun/vendor scope.
- The current work group status allows the requested transition.

Vendor user maintenance should be handled in the internal MES WPF 회원관리 menu:

- The operator marks the account as `외주업체 계정`.
- The operator selects one active VENDOR partner.
- The backend saves the user, roles, and `vendor_user_access` grant together.
- The `VENDOR_PORTAL` role is automatically available from auth seed data and should carry no internal MES menu permissions.
- The helper script `backend/scripts/create_vendor_portal_user.py` remains only for development, testing, or emergency recovery.

## Status Rules

The vendor portal must use the same operational state flow as the internal Bohyun outsource-management menu:

```text
registered / waiting
  -> VENDOR_RECEIVED
    -> WORK_DONE
      -> SHIPPED
```

Blocked transitions:

- Waiting directly to shipped.
- Waiting directly to work done.
- Work done back to inbound.
- Shipped back to any earlier state.
- Any transition on canceled work groups.
- Any transition for another vendor's work group.

## Audit Logging

Add a vendor business audit log separate from login audit logs.

Proposed table:

```text
vendor_portal_audit_log
- vendor_portal_audit_log_id
- user_id
- partner_id
- outsource_work_group_id
- action_type
- before_status
- after_status
- request_ip
- user_agent
- remark
- created_at
```

Minimum actions:

```text
VIEW_LIST
VIEW_DETAIL
INBOUND
WORK_DONE
SHIP
LOGIN_SUCCESS
LOGIN_FAILED, if not already covered by auth audit logs
```

## Vendor WPF App

Create a separate WPF app for vendor use. Do not distribute the internal MES WPF client to Bohyun.

Current project path:

```text
frontend-wpf/Mes.WpfClean/Mes.Wpf/Mes.Vendor.Wpf
```

Minimum screens:

- Login.
- Work group list.
- Work group detail.
- Inbound action.
- Work done action with quantity and optional remark.
- Shipment action.
- Basic error and reconnect handling.

The app should use this public HTTPS host as its API base URL:

```text
https://vendor-mes.semiindustry.com/
```

The app must call only:

```text
POST /api/v1/auth/login
GET  /api/v1/vendor-portal/bohyun-groups
POST /api/v1/vendor-portal/bohyun-groups/{group_id}/inbound
POST /api/v1/vendor-portal/bohyun-groups/{group_id}/work-done
POST /api/v1/vendor-portal/bohyun-groups/ship-batch
```

The vendor WPF app should not use the current public IP directly. The current dynamic public IP, such as `221.154.227.250`, is only a temporary external address and must not be hard-coded.

## Implementation Stages

### Stage 1: Design and Safety Baseline

- Confirm Gabia account access for `semiindustry.com`.
- Create a Cloudflare Free account.
- Inventory existing DNS records before changing nameservers.
- Confirm the Bohyun partner row in `partner`.
- Confirm vendor-visible fields and hidden fields.
- Confirm whether outsource processing fee is visible to Bohyun.

### Stage 2: Backend Foundation

- Add `vendor_user_access`.
- Add `vendor_portal_audit_log`.
- Move existing Bohyun status logic into a shared service.
- Update the internal API to call the shared service.
- Add vendor portal API endpoints that call the same service after vendor-scope checks.
- Add internal WPF 회원관리 support so vendor accounts and partner access are maintained without scripts.
- Keep `backend/scripts/create_vendor_portal_user.py` as a development/testing fallback.
- Add unit/integration tests for status transitions and forbidden cross-vendor access.

### Stage 3: Vendor WPF

- Create a separate vendor WPF project. Completed as `Mes.Vendor.Wpf`.
- Implement login and token handling.
- Implement list/detail/status actions for inbound, work done, and shipment.
- Restrict the app to the public vendor host and vendor portal API routes.
- Add loading, error, empty, and success states.

### Stage 4: Internal Network Verification

- Run backend on an internal-only port.
- Verify the vendor WPF can process inbound, work done, and shipment through the vendor portal API.
- Verify the internal WPF sees the same status changes.
- Verify audit logs are written.

### Stage 5: Cloudflare Tunnel External Access

- Add `semiindustry.com` to Cloudflare.
- Recreate required existing DNS records in Cloudflare.
- Change Gabia nameservers to Cloudflare nameservers.
- Install `cloudflared` on the company MES or proxy server.
- Create a Cloudflare Tunnel.
- Publish `vendor-mes.semiindustry.com` to the internal FastAPI or local reverse proxy URL.
- Test from an external network.

### Stage 6: Pilot Operation

- Issue Bohyun vendor user accounts.
- Install the vendor WPF app on company-managed laptops.
- Run a limited pilot with real but low-risk work groups.
- Review access logs, audit logs, and user feedback.
- Move to normal operation after confirming no cross-scope data exposure.

## Manual Preparation Checklist

- Company public IP.
- Internal reverse proxy server IP.
- Firewall/router admin access.
- Gabia account access for `semiindustry.com`.
- Cloudflare Free account access.
- Existing DNS record inventory for `semiindustry.com`.
- Company server where `cloudflared` will run.
- Optional local reverse proxy choice: Caddy, IIS+ARR, or Nginx.
- Bohyun partner ID.
- Bohyun user account list.
- Laptop deployment method.
- Backup and rollback procedure.
- Contact path for off-hours access issues.

## Rollback Plan

If external access must be stopped:

- Disable the Cloudflare Tunnel route for `vendor-mes.semiindustry.com`.
- Stop or uninstall the `cloudflared` service on the company server.
- Disable Bohyun vendor user accounts or `vendor_user_access` rows.
- Keep audit logs and operational data intact.
