package com.wixpress.workshop

import com.wixpress.hoopoe.json.JsonMapper
import sttp.client3._

import scala.concurrent.{Await, Future}
import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.duration._

object Main extends App {
  println("Hello, world!")

  val backend = HttpClientFutureBackend()
  val mapper = JsonMapper.global

  val future = Future {
    println("hello")
  }

  Await.result(future, 10.seconds)
}