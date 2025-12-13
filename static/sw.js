self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    if (url.search.startsWith("?")) {
        const target = url.search.substring(1);

        event.respondWith(
            fetch(target, {
                method: event.request.method,
                headers: event.request.headers
            })
        );
    }
});
