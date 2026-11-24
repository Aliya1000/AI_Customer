-- ============================================================
-- Initial Sample Data for Testing
-- ============================================================

INSERT INTO products (product_id, product_name, product_description, product_category)
VALUES
    ('PRD-01', 'AeroSound Pro ANC Headphones', 'Wireless Bluetooth 5.3 over-ear headphones with Hybrid Active Noise Cancellation and 1-year hardware warranty.', 'Audio Hardware'),
    ('PRD-02', 'PulseWatch S4 Smartwatch', 'AMOLED fitness smartwatch with 5ATM water resistance and 10-day battery life.', 'Wearables'),
    ('PRD-03', 'CloudDesk CRM Pro Subscription', 'Enterprise multi-seat SaaS subscription with SSO, API access, and 99.9% SLA.', 'SaaS Software')
ON CONFLICT(product_id) DO NOTHING;