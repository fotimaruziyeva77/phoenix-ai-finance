import styles from "./auth-shell.module.css";

type Props = {
  message?: string;
};

/** Shown while reading stored session or during auth redirects — avoids flashing wrong chrome. */
export function AuthSessionLoading({ message = "Checking your session…" }: Props) {
  return (
    <div className={styles.gateLoading} aria-busy="true">
      <div className={styles.spinner} />
      <p className={styles.gateText}>{message}</p>
    </div>
  );
}
