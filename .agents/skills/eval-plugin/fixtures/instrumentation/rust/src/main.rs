use antithesis_instrumentation as _;
use std::{thread, time::Duration};

fn spin(id: u64) {
    let mut x = id;
    loop {
        x = match x % 3 {
            0 => x + 7,
            1 => x * 3,
            _ => x - 1,
        } % 100003;
        thread::sleep(Duration::from_millis(50));
    }
}

fn main() {
    antithesis_sdk::antithesis_init();
    antithesis_sdk::assert_reachable!("rust service started", &serde_json::json!({}));
    let threads: Vec<_> = (1..4).map(|i| thread::spawn(move || spin(i))).collect();
    for t in threads {
        t.join().unwrap();
    }
}
