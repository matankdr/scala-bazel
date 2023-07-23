# Scala Workshop

## Introduction
In this exercise you will implement a basic HTTP request/response flow using STTP client.
You will send http requests to a local instance of HttpBin.
In each case, you are required to send a request and parse the response(s).

## Running local instance of HttpBin
```shell
docker run --rm -p 8080:80 kennethreitz/httpbin
```

## Exercises

<details>
<summary>Exercise 1</summary>

### Base64 Decode
- Send a GET request to `http://localhost:8080/base64/{base64_encoded}`
- Example encoded message: `dmVsbyBpcyBhd2Vzb21lISEhISEK`
- Print the decoded response

</details> 

<details>
<summary>Exercise 2</summary>

### Redirect
- Send a GET request to `http://localhost:8080/redirect-to?url=http%3A%2F%2Flocalhost%3A8080%2Fuuid&status_code=200`
- Mark the request to not follow redirects (`requets.followRedirects(false)`)
- Parse the response
- Send another request according to the value in `Location` header
- 
</details>

<details>
<summary>Exercise 3</summary>

### N redirects
- Send a GET request to `"http://localhost:8080/absolute-redirect/{N}"`
- Mark the request to not follow redirects (`requets.followRedirects(false)`)
- Parse the response
- Send another request according to the value in `Location` header
- Repeat until status code is 200
- print the result JSON
</details>

<details>
<summary>Exercise 4</summary>

### Parse JSON
- Send a GET request to `localhost:8080/stream/{N}`
- Parse the received JSON objects to collection of `HttpBinPayload`
</details>


## All supported endpoints
http://localhost:8080