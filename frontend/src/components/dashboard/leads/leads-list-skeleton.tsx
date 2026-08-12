import styles from "./leads-dashboard.module.css";

export function LeadsListSkeleton() {
  return (
    <div className={styles.skeletonWrap} aria-hidden data-testid="leads-list-skeleton">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className={styles.skeletonRow} />
      ))}
    </div>
  );
}
