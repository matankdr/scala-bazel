package com.wixpress.workshop

import sttp.client3._
import sttp.model.StatusCode

import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.duration._
import scala.concurrent.{Await, Future}

object Solution3 extends App with EitherOps {
  val backend = HttpClientFutureBackend()

  def sendRequest(url: String): Future[Either[String, String]] = {
    val request = basicRequest.get(uri"$url").followRedirects(false)

    for {
      response <- request.send(backend)
      _ = println(s"sent request to $url")
      body <- handleResponse(response)
    } yield body
  }

  def handleResponse(response: Response[Either[String, String]]) = {
    (response.code, response.headers.find(_.is("location"))) match {
      case (StatusCode.Found, Some(location)) =>
        sendRequest(location.value)

      case (StatusCode.Ok, _) =>
        Future.successful(response.body)

      case _ =>
        Future.failed(new RuntimeException("Unexpected response"))
    }
  }

  val result = for {
    response <- sendRequest("http://localhost:8080/absolute-redirect/10")
    body     <- response.toFuture
  } yield println(body)

  Await.result(result, 10.seconds)
}
