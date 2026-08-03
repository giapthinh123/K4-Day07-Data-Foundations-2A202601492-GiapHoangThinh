-- Supabase pgvector schema for 768-dimensional OpenRouter embeddings.
-- Run this file once in Supabase Dashboard -> SQL Editor.

create extension if not exists vector with schema extensions;

create table if not exists public.document_chunks (
  collection_name text not null,
  chunk_id text not null,
  doc_id text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding extensions.vector(768) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (collection_name, chunk_id)
);

create index if not exists document_chunks_doc_id_idx
  on public.document_chunks (collection_name, doc_id);

create index if not exists document_chunks_metadata_idx
  on public.document_chunks using gin (metadata);

create index if not exists document_chunks_embedding_hnsw_idx
  on public.document_chunks using hnsw (embedding vector_cosine_ops);

create or replace function public.set_document_chunks_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists document_chunks_updated_at on public.document_chunks;
create trigger document_chunks_updated_at
before update on public.document_chunks
for each row execute function public.set_document_chunks_updated_at();

alter table public.document_chunks enable row level security;

create or replace function public.match_document_chunks(
  p_query_embedding extensions.vector(768),
  p_match_count integer default 5,
  p_collection_name text default 'documents',
  p_filter_metadata jsonb default '{}'::jsonb
)
returns table (
  id text,
  content text,
  metadata jsonb,
  similarity double precision
)
language sql
stable
set search_path = public, extensions
as $$
  select
    chunks.chunk_id as id,
    chunks.content,
    chunks.metadata,
    1 - (chunks.embedding <=> p_query_embedding) as similarity
  from public.document_chunks as chunks
  where chunks.collection_name = p_collection_name
    and chunks.metadata @> coalesce(p_filter_metadata, '{}'::jsonb)
  order by chunks.embedding <=> p_query_embedding
  limit greatest(least(p_match_count, 200), 0);
$$;

revoke all on table public.document_chunks from anon, authenticated;
revoke all on function public.match_document_chunks(
  extensions.vector, integer, text, jsonb
) from anon, authenticated;

grant all on table public.document_chunks to service_role;
grant execute on function public.match_document_chunks(
  extensions.vector, integer, text, jsonb
) to service_role;
