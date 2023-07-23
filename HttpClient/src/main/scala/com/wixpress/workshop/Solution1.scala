package com.wixpress.workshop

import sttp.client3._

import scala.concurrent.Await
import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.duration._

object Solution1 extends App with EitherOps {
  val backend = HttpClientFutureBackend()
  val encoded = "dmVsbyBpcyBhd2Vzb21lISEhISEK"

  val request = basicRequest.get(uri"http://localhost:8080/base64/$encoded")

  val result = for {
    response <- request.send(backend)
    body     <- response.body.toFuture
  } yield println(body)

  Await.result(result, 10.seconds)
}
