package com.wixpress.workshop

import sttp.client3._
import sttp.model.StatusCode

import scala.concurrent.{Await, Future}
import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.duration._

object Solution2 extends App with OptionOps with EitherOps {
  val backend = HttpClientFutureBackend()

  val request = basicRequest.get(uri"http://localhost:8080/redirect-to?url=http%3A%2F%2Flocalhost%3A8080%2Fuuid&status_code=200")
    .followRedirects(false)

  val result = for {
    response1       <- request.send(backend)
    locationHeader  <- response1.headers.find(_.is("location")).toFuture if response1.code == StatusCode.Found
    location         = locationHeader.value
    response2       <- basicRequest.get(uri"$location").send(backend)
    body            <- response2.body.toFuture
  } yield println(body)

  Await.result(result, 10.seconds)
}
