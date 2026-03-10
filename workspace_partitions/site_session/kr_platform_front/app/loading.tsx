export default function Loading() {
  return (
    <div className="page-loading" role="status" aria-label="페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">불러오는 중…</p>
    </div>
  );
}
