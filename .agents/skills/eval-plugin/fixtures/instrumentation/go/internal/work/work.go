// Package work is shared by both Go programs, so it loads as one module in two containers.
package work

import "time"

// Spin runs a little branching work forever on n goroutines.
func Spin(n int) {
	for i := 0; i < n; i++ {
		go func(x int) {
			for {
				switch x % 3 {
				case 0:
					x += 7
				case 1:
					x *= 3
				default:
					x--
				}
				x %= 100003
				time.Sleep(50 * time.Millisecond)
			}
		}(i)
	}
}
