package com.wixpress.workshop

import scala.concurrent.Future

trait OptionOps {
  implicit class OptionOps[T](opt: Option[T]) {
    def toFuture = opt match {
      case Some(value) => Future.successful(value)
      case None        => Future.failed(new RuntimeException("Empty option"))
    }
  }
}
