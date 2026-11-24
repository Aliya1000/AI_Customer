-- ==============================================================================
-- 02. Supabase Row Level Security (RLS) Policies
-- ==============================================================================

-- Enable RLS across all tables
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coaching_reports ENABLE ROW LEVEL SECURITY;

-- 1. Products Policy: Public Read, Authenticated/Service Role Write
CREATE POLICY "Allow public read access to products"
    ON public.products FOR SELECT
    USING (true);

CREATE POLICY "Allow service role full access to products"
    ON public.products FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 2. Sessions Policy: Authenticated users & Service role access
CREATE POLICY "Allow service role full access to sessions"
    ON public.sessions FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow anonymous read access to active sessions"
    ON public.sessions FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow creation of sessions"
    ON public.sessions FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Allow updating sessions"
    ON public.sessions FOR UPDATE
    TO anon, authenticated
    USING (true);

-- 3. Messages Policy
CREATE POLICY "Allow service role full access to messages"
    ON public.messages FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow read access to messages"
    ON public.messages FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow insert access to messages"
    ON public.messages FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- 4. Knowledge Documents Policy
CREATE POLICY "Allow service role full access to knowledge_documents"
    ON public.knowledge_documents FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow read access to knowledge_documents"
    ON public.knowledge_documents FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow write access to knowledge_documents"
    ON public.knowledge_documents FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "Allow delete access to knowledge_documents"
    ON public.knowledge_documents FOR DELETE
    TO anon, authenticated
    USING (true);

-- 5. Coaching Reports Policy
CREATE POLICY "Allow service role full access to coaching_reports"
    ON public.coaching_reports FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow read access to coaching_reports"
    ON public.coaching_reports FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Allow write access to coaching_reports"
    ON public.coaching_reports FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);
