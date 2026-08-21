import type { WorkSnapshot } from "../contracts/work";

type Props = { snapshot: WorkSnapshot };

export default function OwnerWorkFeed({ snapshot }: Props) {
  return (
    <section className="owner-work-feed">
      <h3>当前工作</h3>
      {snapshot.items.length === 0 ? (
        <p>暂无正在处理的工作。</p>
      ) : (
        snapshot.items.map((item) => (
          <article key={item.id}>
            <strong>{item.title}</strong>
            <p>{item.status}</p>
          </article>
        ))
      )}
    </section>
  );
}
