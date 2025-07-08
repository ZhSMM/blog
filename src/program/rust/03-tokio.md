# Tokio

#### 引入tokio

```
// 通过命令行导入
cargo add tokio -F full

// 在Cargo.toml中添加
[dependencies]
tokio = { version = "1.44.1", features = ["full"] }
```

#### 理解Runtime

tokio的两个核心概念：runtime和task。

##### 创建Runtime

Tokio可以创建多线程Runtime和单一线程Runtime（也叫current thread runtime）：每一个异步任务都是一个线程内的**协程**，单一线程的runtime是在单个线程内调度管理这些任务，多线程runtime则是在多个线程内不断地分配和跨线程传递这些任务。

```rust
use tokio;

// 创建单线程Runtime
#[tokio::main(flavor = "current_thread")]
async fn main() {}

// 等价于
fn main() {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap()
        .block_on(async { ... })
}

// 创建多线程Runtime
// 不指定线程数时默认创建cpu核数的线程数
#[tokio::main]
#[tokio::main(flavor = "multi_thread"] // 等价于#[tokio::main]
#[tokio::main(flavor = "multi_thread", worker_threads = 10))]
#[tokio::main(worker_threads = 10))]
async fn main() {}

// 等价于
fn main(){
  tokio::runtime::Builder::new_multi_thread()
        .worker_threads(N)  
        .enable_all()
        .build()
        .unwrap()
        .block_on(async { ... });
}
```

创建多个Runtime共存：

```rust
use std::thread;
use std::time::Duration;
use tokio::runtime::Runtime;

fn main() {
  // 在第一个线程内创建一个多线程的runtime
  let t1 = thread::spawn(||{
    let rt = Runtime::new().unwrap();
    thread::sleep(Duration::from_secs(10));
  });

  // 在第二个线程内创建一个单线程的runtime，此时可以充分利用CPU
  let t2 = thread::spawn(||{
    let rt = Runtime::Builder::new().new_current_thread().enable_all().build().unwrap();
    thread::sleep(Duration::from_secs(10));
  });

  t1.join().unwrap();
  t2.join().unwrap();
}
```

##### Runtime使用

使用`tokio::time::sleep()`来模拟耗时操作：

> `std::time::sleep()` 会阻塞当前线程，而`tokio::time::sleep()`只会让当前任务放弃cpu并进入调度队列等待被唤醒，不会阻塞工作线程，即该线程可以执行其他异步任务。

```rust
use tokio::runtime::Runtime;
use chrono::Local;

fn main() {
    let rt = Runtime::new().unwrap();
    rt.block_on(async {
        println!("before sleep: {}", Local::now().format("%F %T.%3f"));
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
        println!("after sleep: {}", Local::now().format("%F %T.%3f"));
    });
}
```

Runtime的block_on方法要求一个Future为参数，可以像上面一样直接使用一个`async {}`来定义一个Future。每一个`Future`都是一个已经定义好但尚未执行的异步任务，每一个异步任务中可能会包含其它子任务。

这些异步任务不会直接执行，需要先将它们放入到runtime环境，然后在合适的地方通过Future的await来执行它们。await可以将已经定义好的异步任务立即加入到runtime的任务队列中等待调度执行，于此同时，await会等待该异步任务完成才返回。

`block_on`会阻塞当前线程(例如阻塞住上面的main函数所在的主线程)，直到其指定的**异步任务树(可能有子任务)**全部完成，并返回所执行异步任务的返回值。

##### spawn：向runtime中添加新的异步任务

在上面的例子中，直接将`async {}`作为`block_on()`的参数，这个`async {}`本质上是一个Future，即一个异步任务。在这个最外层的异步任务内部，还可以创建新的异步任务，它们都将在同一个runtime中执行。

有时候，定义要执行的异步任务时，并未身处runtime内部。例如定义一个异步函数，此时可以使用`tokio::spawn()`来生成异步任务。

```rust
use std::thread;

use chrono::Local;
use tokio::{self, runtime::Runtime, time};

fn now() -> String {
    Local::now().format("%F %T").to_string()
}

// 在runtime外部定义一个异步任务，且该函数返回值不是Future类型
fn async_task() {
  println!("create an async task: {}", now());
  tokio::spawn(async {
    time::sleep(time::Duration::from_secs(10)).await;
    println!("async task over: {}", now());
  });
}

fn main() {
    let rt1 = Runtime::new().unwrap();
    rt1.block_on(async {
      // 调用函数，该函数内创建了一个异步任务，将在当前runtime内执行
      async_task();
    });
}
```

除了`tokio::spawn()`，runtime自身也能spawn，因此，也可以传递runtime(注意，要传递runtime的引用)，然后使用runtime的`spawn()`：

```rust
use tokio::{Runtime, time}
fn async_task(rt: &Runtime) {
  rt.spawn(async {
    time::sleep(time::Duration::from_secs(10)).await;
  });
}

fn main(){
  let rt = Runtime::new().unwrap();
  rt.block_on(async {
    async_task(&rt);
  });
}
```

##### 进入runtime: 非阻塞的enter()

`block_on()`进入runtime时，会阻塞当前线程，`enter()`进入runtime时，不会阻塞当前线程，它会返回一个`EnterGuard`。EnterGuard没有其它作用，它仅仅只是声明从它开始的所有异步任务都将在runtime上下文中执行，直到删除该EnterGuard。

删除EnterGuard并不会删除runtime，只是释放之前的runtime上下文声明。因此，删除EnterGuard之后，可以声明另一个EnterGuard，这可以再次进入runtime的上下文环境。

```rust
use tokio::{self, runtime::Runtime, time};
use chrono::Local;
use std::thread;

fn now() -> String {
  Local::now().format("%F %T").to_string()
}

fn main() {
    let rt = Runtime::new().unwrap();

    // 进入runtime，但不阻塞当前线程
    let guard1 = rt.enter();

    // 生成的异步任务将放入当前的runtime上下文中执行
    tokio::spawn(async {
      time::sleep(time::Duration::from_secs(5)).await;
      println!("task1 sleep over: {}", now());
    });

    // 释放runtime上下文，这并不会删除runtime
    drop(guard1);

    // 可以再次进入runtime
    let guard2 = rt.enter();
    tokio::spawn(async {
      time::sleep(time::Duration::from_secs(4)).await;
      println!("task2 sleep over: {}", now());
    });

    drop(guard2);

    // 阻塞当前线程，等待异步任务的完成
    thread::sleep(std::time::Duration::from_secs(10));
}
```

##### tokio的两种线程：worker thread和blocking thread

tokio提供了两种功能的线程：

- 用于异步任务的工作线程(worker thread)：用于执行不会阻塞线程的任务，在遇到阻塞时会放弃cpu并进入调度队列，如`tokio::time::sleep()`
- 用于同步任务的阻塞线程(blocking thread)：用于长时间计算的或阻塞整个线程的任务

blocking thread默认是不存在的，只有在调用了`spawn_blocking()`时才会创建一个对应的blocking thread。

```rust
use std::thread;
use chrono::Local;
use tokio::{self, runtime::Runtime, time};

fn now() -> String {
    Local::now().format("%F %T").to_string()
}

fn main() {
    let rt1 = Runtime::new().unwrap();
    // 创建一个blocking thread，可立即执行(由操作系统调度系统决定何时执行)
    // 注意，不阻塞当前线程
    let task = rt1.spawn_blocking(|| {
      println!("in task: {}", now());
      // 注意，是线程的睡眠，不是tokio的睡眠，因此会阻塞整个线程
      thread::sleep(std::time::Duration::from_secs(10))
    });

    // 小睡1毫秒，让上面的blocking thread先运行起来
    std::thread::sleep(std::time::Duration::from_millis(1));
    println!("not blocking: {}", now());

    // 可在runtime内等待blocking_thread的完成
    rt1.block_on(async {
      task.await.unwrap();
      println!("after blocking task: {}", now());
    });
}
```

##### 关闭Runtime

由于异步任务完全依赖于Runtime，而Runtime又是程序的一部分，它可以轻易地被删除(drop)，这时Runtime会被关闭(shutdown)。

关闭Runtime时，将使得该Runtime中的所有**异步任务**被移除。完整的关闭过程如下：

- 先移除整个任务队列，保证不再产生也不再调度新任务
- 移除当前正在执行但尚未完成的**异步任务**，即终止所有的worker thread
- 移除Reactor，禁止接收事件通知

注意，这种删除runtime句柄的方式只会立即关闭未被阻塞的worker thread，那些已经运行起来的blocking thread以及已经阻塞整个线程的worker thread仍然会执行。但是，删除runtime又要等待runtime中的所有异步和非异步任务(会阻塞线程的任务)都完成，因此删除操作会阻塞当前线程。

```rust
use chrono::Local;
use std::thread;
use tokio::{self, runtime::Runtime, time};

fn now() -> String {
    Local::now().format("%F %T").to_string()
}

fn main() {
    let rt = Runtime::new().unwrap();
    // 一个运行5秒的blocking thread
    // 删除rt时，该任务将继续运行，直到自己终止
    rt.spawn_blocking(|| {
        thread::sleep(std::time::Duration::from_secs(5));
        println!("blocking thread task over: {}", now());
    });

    // 进入runtime，并生成一个运行3秒的异步任务，
    // 删除rt时，该任务直接被终止
    let _guard = rt.enter();
    rt.spawn(async {
        time::sleep(time::Duration::from_secs(3)).await;
        println!("worker thread task over 1: {}", now());
    });

    // 进入runtime，并生成一个运行4秒的阻塞整个线程的任务
    // 删除rt时，该任务继续运行，直到自己终止
    rt.spawn(async {
        std::thread::sleep(std::time::Duration::from_secs(4));
        println!("worker thread task over 2: {}", now());
    });

    // 先让所有任务运行起来
    std::thread::sleep(std::time::Duration::from_millis(3));

    // 删除runtime句柄，将直接移除那个3秒的异步任务，
    // 且阻塞5秒，直到所有已经阻塞的thread完成
    drop(rt);
    println!("runtime droped: {}", now());
}
```

shutdown_timeout()：等待指定的时间，如果正在超时时间内还未完成关闭，将强行终止runtime中的所有线程

shutdown_background()：立即强行关闭runtime

```rust
use chrono::Local;
use std::thread;
use tokio::{self, runtime::Runtime, time};

fn now() -> String {
    Local::now().format("%F %T").to_string()
}

fn main() {
    let rt = Runtime::new().unwrap();

    rt.spawn_blocking(|| {
        thread::sleep(std::time::Duration::from_secs(5));
        println!("blocking thread task over: {}", now());
    });

    let _guard = rt.enter();
    rt.spawn(async {
        time::sleep(time::Duration::from_secs(3)).await;
        println!("worker thread task over 1: {}", now());
    });

    rt.spawn(async {
        std::thread::sleep(std::time::Duration::from_secs(4));
        println!("worker thread task over 2: {}", now());
    });

    // 先让所有任务运行起来
    std::thread::sleep(std::time::Duration::from_millis(3));

    // 1秒后强行关闭Runtime
    rt.shutdown_timeout(std::time::Duration::from_secs(1));
    println!("runtime droped: {}", now());
}
```



##### Runtime Handle

tokio提供了一个称为runtime Handle的东西，它实际上是runtime的一个引用，可以随意被clone。它可以`spawn()`生成异步任务，这些异步任务将绑定在其所引用的runtime中，还可以`block_on()`或`enter()`进入其所引用的runtime，此外，还可以生成blocking thread。

```rust
let rt = Runtime::new().unwrap();
let handle = rt.handle();
handle.spawn(...)
handle.spawn_blocking(...)
handle.block_on(...)
handle.enter()
```

需注意，如果runtime已被关闭，handle也将失效，此后再使用handle，将panic。