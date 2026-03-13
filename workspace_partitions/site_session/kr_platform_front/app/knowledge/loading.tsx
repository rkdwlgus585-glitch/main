export default function KnowledgeLoading() {
  return (
    <div className="page-loading" role="status" aria-label="건설실무 페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">건설실무 콘텐츠를 불러오고 있습니다</p>
    </div>
  );
}
