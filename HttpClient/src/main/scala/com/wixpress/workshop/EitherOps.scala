package com.wixpress.workshop

import scala.concurrent.Future

trait EitherOps {
  implicit class EitherOps[S, T](e: Either[S, T]) {
    def toFuture = e match {
      case Left(s) =>
        Future.failed(new RuntimeException(s.toString))
      case Right(t) =>
        Future.successful(t)
    }
  }
}
